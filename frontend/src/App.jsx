import { useState } from "react";
import "./App.css";

function App() {
  const [text, setText] = useState("");
  const [ngramN, setNgramN] = useState(2);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const checkText = async () => {
    if (!text.trim()) {
      setError("Введіть текст для перевірки");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch("http://127.0.0.1:8000/check", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          text: text,
          ngram_n: Number(ngramN)
        })
      });

      if (!response.ok) {
        throw new Error("Помилка при перевірці");
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError("Не вдалося підключитися до бекенду");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <div className="container">
        <h1>Система перевірки тексту</h1>

        <div className="card">
          <label>Введіть текст:</label>

          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Вставте текст..."
          />

          <label>Оберіть n-граму:</label>

          <select value={ngramN} onChange={(e) => setNgramN(e.target.value)}>
            <option value={2}>2</option>
            <option value={3}>3</option>
            <option value={4}>4</option>
          </select>

          <button onClick={checkText} disabled={loading}>
            {loading ? "Обробка..." : "Перевірити"}
          </button>

          {error && <p className="error">{error}</p>}
        </div>

        {result && (
          <div className="result">
            <h2>Результат</h2>

            <p>
              <b>Файл:</b> {result.most_similar_file}
            </p>

            <p>
              <b>Схожість:</b> {result.similarity}%
            </p>

            <p>
              <b>Унікальність:</b> {result.uniqueness}%
            </p>

            <h3>Усі результати:</h3>

            <ul>
              {result.all_results.map((item, i) => (
                <li key={i}>
                  {item.filename} — {item.similarity}%
                </li>
              ))}
            </ul>

            <h3>Спільні слова:</h3>

            <div className="words">
              {result.common_words.length > 0 ? (
                result.common_words.map((w, i) => (
                  <span key={i}>
                    {w.word} ({w.count})
                  </span>
                ))
              ) : (
                <p>Немає</p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;