import pandas as pd
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# --- Locality Preprocessing ---
def preprocess_locality(text):
    text = text.lower()

    # Preserve named geographic features
    geo_terms = ['canyon', 'creek', 'river', 'ranch', 'valley', 'park', 'lake', 'mountain', 'mesa', 'draw']
    tokens = text.split()
    processed_tokens = []
    skip_next = False
    for i in range(len(tokens)):
        if skip_next:
            skip_next = False
            continue
        token = tokens[i].strip('.')
        next_token = tokens[i + 1].strip('.') if i + 1 < len(tokens) else ""
        if token in ['north', 'south', 'east', 'west', 'northeast', 'northwest', 'southeast', 'southwest'] and next_token in geo_terms:
            processed_tokens.append(token + ' ' + next_token)
            skip_next = True
        else:
            processed_tokens.append(token)

    text = ' '.join(processed_tokens)

    # Normalize compass directions (including forms with periods)
    direction_map = {
        r'\bn\.?\b': 'n', r'\bs\.?\b': 's',
        r'\be\.?\b': 'e', r'\bw\.?\b': 'w',
        r'\bnw\.?\b': 'nw', r'\bsw\.?\b': 'sw',
        r'\bne\.?\b': 'ne', r'\bse\.?\b': 'se',
        r'\bnorth\b': 'n', r'\bsouth\b': 's',
        r'\beast\b': 'e', r'\bwest\b': 'w',
        r'\bnorthwest\b': 'nw', r'\bsouthwest\b': 'sw',
        r'\bnortheast\b': 'ne', r'\bsoutheast\b': 'se'
    }
    for pattern, replacement in direction_map.items():
        text = re.sub(pattern, replacement, text)

    # Normalize distance units (miles, air miles, km)
    text = re.sub(r'(\d+(\.\d+)?)(\s*)?(air\s*miles?|mi\.?|miles?)', r'\1mi', text)
    text = re.sub(r'(\d+(\.\d+)?)(\s*)?(kilometers?|kilometres?|km\.?)', r'\1km', text)

    # Clean up punctuation
    text = re.sub(r'[^a-z0-9.\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# --- Distance and Direction Extraction ---
def extract_distance_direction(text):
    # Match directions with 2-letter compass points first, then single
    match = re.search(
        r'(\d+(\.\d+)?)(mi|km)\s*((nw|ne|sw|se|n|s|e|w))?\s*(of)?\s*(\w+)?',
        text
    )
    if match:
        distance = float(match.group(1))
        unit = match.group(3)
        direction = match.group(4) or ''
        return f"{distance:.1f}{unit}_{direction}"
    return None


# --- Locality Grouping Function ---
def group_localities(df):
    df['normalized_locality'] = df['locality'].fillna("").astype(str).apply(preprocess_locality)
    df['distance_direction_key'] = df['normalized_locality'].apply(extract_distance_direction)

    vectorizer = TfidfVectorizer().fit_transform(df['normalized_locality'])
    similarity_matrix = cosine_similarity(vectorizer)

    threshold = 0.75
    groups = [-1] * len(df)
    group_id = 0

    for i in range(len(df)):
        if groups[i] == -1:
            groups[i] = group_id
            for j in range(i + 1, len(df)):
                if groups[j] == -1 and similarity_matrix[i, j] > threshold:
                    if df.at[i, 'distance_direction_key'] == df.at[j, 'distance_direction_key']:
                        groups[j] = group_id
            group_id += 1

    df['suggested group'] = groups
    return df

# --- Main Execution ---
if __name__ == "__main__":
    file_path = input("Enter the path to your CSV file: ").strip()

    try:
        df = pd.read_csv(file_path)
        if 'locality' not in df.columns:
            print("Error: The file does not contain a 'locality' column.")
        else:
            df = group_localities(df)
            output_path = file_path.replace(".csv", "-grouped.csv")
            df.to_csv(output_path, index=False)
            print(f"\n✅ Grouped file saved as:\n{output_path}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
