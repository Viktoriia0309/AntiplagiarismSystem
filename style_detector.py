from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


STYLE_EXAMPLES = {
    "Науковий": [
        "У роботі досліджено методи аналізу текстових даних та алгоритми обробки природної мови.",
        "Результати експерименту підтверджують ефективність запропонованого методу."
    ],
    "Розмовний": [
        "Привіт, як справи? Я сьогодні дуже втомилась, але день був нормальний.",
        "Ну я не знаю, може зробимо це завтра, бо зараз якось не дуже хочеться."
    ],
    "Офіційно-діловий": [
        "Відповідно до наказу необхідно подати заяву та затвердити документ у встановлений термін.",
        "Прошу надати дозвіл на проходження практики згідно з навчальним планом."
    ],
    "Публіцистичний": [
        "Сучасне суспільство потребує нових підходів до вирішення важливих соціальних проблем.",
        "Сьогодні питання інформаційної безпеки набуває особливої актуальності."
    ],
    "Художній": [
        "Тиха ніч огорнула місто, а в серці народжувався легкий смуток.",
        "Вона дивилася у вікно, де за склом повільно танув вечір."
    ],
    "Церковний": [
        "Господь дарує людині віру, надію і духовне очищення через молитву.",
        "Святий дух наповнює душу миром, любов’ю та покаянням."
    ]
}


def detect_text_style(input_text: str):
    style_names = []
    style_texts = []

    for style, examples in STYLE_EXAMPLES.items():
        for example in examples:
            style_names.append(style)
            style_texts.append(example)

    all_texts = style_texts + [input_text]

    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform(all_texts)

    input_vector = vectors[-1]
    style_vectors = vectors[:-1]

    similarities = cosine_similarity(input_vector, style_vectors)[0]

    style_scores = {}

    for style, similarity in zip(style_names, similarities):
        if style not in style_scores:
            style_scores[style] = []
        style_scores[style].append(similarity)

    average_scores = {
        style: sum(scores) / len(scores)
        for style, scores in style_scores.items()
    }

    best_style = max(average_scores, key=average_scores.get)

    return {
        "style": best_style,
        "scores": {
            style: round(score * 100, 2)
            for style, score in average_scores.items()
        }
    }