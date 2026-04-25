import os
import re
import stanza
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from collections import Counter
from stop_words import get_stop_words

stanza.download('uk')
nlp = stanza.Pipeline('uk', processors='tokenize,lemma', use_gpu=False)

STOP_WORDS = set(get_stop_words('uk'))

model = SentenceTransformer('all-MiniLM-L6-v2')


def read_texts_from_folder(folder_path):
    texts = []
    filenames = []

    if not os.path.exists(folder_path):
        print(f"Помилка: папка '{folder_path}' не знайдена.")
        return texts, filenames

    for filename in sorted(os.listdir(folder_path)):
        if filename.endswith(".txt"):
            file_path = os.path.join(folder_path, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    text = file.read().strip()
                    if text:
                        texts.append(text)
                        filenames.append(filename)
            except Exception as e:
                print(f"Помилка при зчитуванні файлу {filename}: {e}")

    return texts, filenames


def read_input_text(file_path):
    if not os.path.exists(file_path):
        print(f"Помилка: файл '{file_path}' не знайдений.")
        return ""

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read().strip()
    except Exception as e:
        print(f"Помилка при зчитуванні вхідного тексту: {e}")
        return ""


def preprocess_text(text):
    text = text.lower()
    text = re.sub(r"[^\w\sа-яіїєґ']", " ", text, flags=re.UNICODE)
    text = re.sub(r"\d+", " ", text)

    # лематизація прямо тут
    doc = nlp(text)

    words = []
    for sentence in doc.sentences:
        for word in sentence.words:
            lemma = word.lemma
            if lemma not in STOP_WORDS:
                words.append(lemma)

    return " ".join(words)

def get_common_words(text1, text2):
    words1 = preprocess_text(text1).split()
    words2 = preprocess_text(text2).split()

    counter1 = Counter(words1)
    counter2 = Counter(words2)

    common = {}
    for word in set(counter1) & set(counter2):
        common[word] = min(counter1[word], counter2[word])

    # сортуємо за частотою
    common_sorted = sorted(common.items(), key=lambda x: x[1], reverse=True)

    return common_sorted

def compute_tfidf(texts):
    vectorizer = TfidfVectorizer()
    return vectorizer.fit_transform(texts)

def cosine_sim(input_vector, database_vectors):
    return cosine_similarity(input_vector, database_vectors)[0]

def get_ngrams(text, n=2):
    words = text.split()
    return set(zip(*[words[i:] for i in range(n)]))

def jaccard_similarity(text1, text2, n=2):
    ngrams1 = get_ngrams(text1, n)
    ngrams2 = get_ngrams(text2, n)

    if not ngrams1 or not ngrams2:
        return 0.0

    intersection = len(ngrams1 & ngrams2)
    union = len(ngrams1 | ngrams2)

    return intersection / union

def semantic_similarity(database_texts, input_text):
    embeddings = model.encode(database_texts + [input_text])

    input_vec = embeddings[-1]
    db_vecs = embeddings[:-1]

    similarities = cosine_similarity([input_vec], db_vecs)[0]
    return similarities

def calculate_full_similarity(database_texts, input_text):
    processed_database = [preprocess_text(t) for t in database_texts]
    processed_input = preprocess_text(input_text)

    all_texts = processed_database + [processed_input]

    tfidf_matrix = compute_tfidf(all_texts)

    input_vec = tfidf_matrix[-1]
    db_vecs = tfidf_matrix[:-1]

    cosine_scores = cosine_sim(input_vec, db_vecs)

    # n-gram
    jaccard_scores = [
        jaccard_similarity(processed_input, text, n=2)
        for text in processed_database
    ]

    # semantic
    semantic_scores = semantic_similarity(database_texts, input_text)

    # combine
    combined = [
        (c + j + s)/3
        for c, j, s in zip(cosine_scores, jaccard_scores, semantic_scores)
    ]

    return combined


def print_results(filenames, similarities, database_texts, input_text):
    results = list(zip(filenames, similarities, database_texts))
    results.sort(key=lambda x: x[1], reverse=True)

    max_similarity = results[0][1]
    most_similar_file = results[0][0]
    most_similar_text = results[0][2]
    uniqueness = max(0.0, 1 - max_similarity) * 100

    input_words = preprocess_text(input_text).split()
    similar_words = preprocess_text(most_similar_text).split()

    common_words = Counter(input_words) & Counter(similar_words)

    with open("results.txt", "w", encoding="utf-8") as f:
        f.write("Результати порівняння:\n")
        f.write("-" * 60 + "\n")

        for filename, similarity, _ in results:
            line = f"{filename:<15} | Схожість: {similarity:.4f} | {similarity * 100:.2f}%\n"
            f.write(line)

        f.write("-" * 60 + "\n")
        f.write(f"Найбільш схожий документ: {most_similar_file}\n")
        f.write(f"Максимальна схожість: {max_similarity:.4f} | {max_similarity * 100:.2f}%\n")
        f.write(f"Унікальність тексту: {uniqueness:.2f}%\n")
        f.write("Спільні слова між вхідним текстом і найбільш схожим документом:\n")

        if common_words:
            line = ", ".join([f"{word}({count})" for word, count in common_words.most_common()])
            f.write(line + ".\n")
        else:
            f.write("Немає спільних слів.\n")
        
    print("\nРезультат:")
    print("-" * 40)
    print(f"Найбільш схожий документ: {most_similar_file}")
    print(f"Схожість: {max_similarity * 100:.2f}%")
    print(f"Унікальність: {uniqueness:.2f}%")
    print("Повний звіт записано в results.txt")


def main():
    folder_path = "texts"
    input_file = "input_text.txt"

    database_texts, filenames = read_texts_from_folder(folder_path)
    input_text = read_input_text(input_file)

    if not database_texts:
        print("База текстів порожня або не зчитана.")
        return

    if not input_text:
        print("Вхідний текст порожній або не зчитаний.")
        return

    similarities = calculate_full_similarity(database_texts, input_text)
    print_results(filenames, similarities, database_texts, input_text)


if __name__ == "__main__":
    main()