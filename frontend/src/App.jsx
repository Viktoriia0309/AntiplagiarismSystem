import { useState } from "react";
import "./App.css";
import font from "./fonts/Roboto-Regular.ttf?url";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import {
  PieChart,
  Pie,
  Tooltip,
  Legend
} from "recharts";

const COLORS = [
  "#A8DADC",
  "#F4A261",
  "#E9C46A",
  "#BDE0FE",
  "#CDB4DB",
  "#FFAFCC",
  "#B7E4C7",
  "#FFD6A5",
  "#90DBF4",
  "#D8E2DC"
];
const getColor = (index) => COLORS[index % COLORS.length];

const loadFont = async (doc) => {
  const response = await fetch(font);
  const buffer = await response.arrayBuffer();

  const base64 = btoa(
    new Uint8Array(buffer).reduce(
      (data, byte) => data + String.fromCharCode(byte),
      ""
    )
  );

  doc.addFileToVFS("Roboto-Regular.ttf", base64);
  doc.addFont("Roboto-Regular.ttf", "Roboto", "normal");
  doc.setFont("Roboto");
};

function App() {
  const [text, setText] = useState("");
  const [ngramN, setNgramN] = useState(2);
  const [mode, setMode] = useState("plagiarism");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [progress, setProgress] = useState(0);
  const [page, setPage] = useState("main");
  const [hoveredWord, setHoveredWord] = useState(null);
  const [file, setFile] = useState(null);
  const [inputType, setInputType] = useState("text");

  const highlightText = (text, positions) => {
    if (!positions || positions.length === 0 || !text) {
      return text;
    }

    const sorted = [...positions].sort((a, b) => a.start - b.start);

    const result = [];
    let lastIndex = 0;

    sorted.forEach((pos, index) => {
      result.push(text.slice(lastIndex, pos.start));

      result.push(
        <span key={index} className="highlighted-word">
          {text.slice(pos.start, pos.end)}
        </span>
      );

      lastIndex = pos.end;
    });

    result.push(text.slice(lastIndex));

    return result;
  };

  const exportReportToPDF = async () => {
    if (!result) return;

    const doc = new jsPDF({
      unit: "pt",
      format: "a4"
    });

    await loadFont(doc);

    doc.setFontSize(18);
    doc.text("Звіт про перевірку тексту", 40, 40);

    doc.setFontSize(12);
    doc.text(`Файл: ${result.most_similar_file}`, 40, 70);
    doc.text(`Схожість: ${result.similarity}%`, 40, 90);
    doc.text(`Унікальність: ${result.uniqueness}%`, 40, 110);

    autoTable(doc, {
      startY: 140,

      head: [["№", "Файл", "Схожість"]],
      body: result.all_results.map((item, index) => [
        index + 1,
        item.filename,
        `${item.similarity}%`
      ]),

      styles: {
        font: "Roboto",
        fontStyle: "normal",
        fontSize: 10
      },

      headStyles: {
        font: "Roboto",
        fontStyle: "normal",
        fillColor: [37, 99, 235],
        textColor: [255, 255, 255]
      },

      bodyStyles: {
        font: "Roboto",
        fontStyle: "normal"
      }
    });
    
    const finalY = doc.lastAutoTable.finalY + 20;

    if (result.mode === "plagiarism") {
      doc.text("Спільні слова:", 40, finalY);

      const commonWordsText =
        result.common_words.length > 0
          ? result.common_words
              .map((item) => `${item.word} (${item.count})`)
              .join(", ")
          : "Немає спільних слів";

      const splitWords = doc.splitTextToSize(commonWordsText, 500);
      doc.text(splitWords, 40, finalY + 20);
    }

    doc.save("report.pdf");
  };

  const checkText = async () => {
    if (inputType === "text" && !text.trim()) {
      setError("Введіть текст для перевірки");
      return;
    }

    if (inputType === "file" && !file) {
      setError("Завантажте файл для перевірки");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);
    setProgress(0);


    try {
      let response;

      if (inputType === "text") {
        response = await fetch("http://127.0.0.1:8000/check-progress", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            text: text,
            ngram_n: Number(ngramN),
            mode: mode
          })
        });
      } else {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("ngram_n", Number(ngramN));
        formData.append("mode", mode);

        response = await fetch("http://127.0.0.1:8000/check-file-progress", {
          method: "POST",
          body: formData
        });
      }

      if (!response.ok) {
        throw new Error("Помилка при перевірці");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");

      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop();

        for (const line of lines) {
          if (!line.trim()) continue;

          const data = JSON.parse(line);

          if (data.type === "progress") {
            setProgress(data.progress);
          }

          if (data.type === "result") {
            setProgress(100);
            setResult(data);
            setHoveredWord(null);
          }

          if (data.type === "error") {
            setError(data.message);
          }
        }
      }

    } catch (err) {
      setError("Не вдалося підключитися до бекенду");
    } finally {
      

      setTimeout(() => {
        setLoading(false);
      }, 500);
    }
  };

  if (page === "allResults" && result) {
    return (
      <div className="page">
        <div className="container">
          <button className="back-button" onClick={() => setPage("report")}>
            ← Назад до звіту
          </button>

          <div className="report-page">
            <h1>Усі опрацьовані тексти</h1>

            <div className="report-section">
              <table>
                <thead>
                  <tr>
                    <th>№</th>
                    <th>Назва файлу</th>
                    <th>Схожість</th>
                  </tr>
                </thead>

                <tbody>
                  {result.all_results.map((item, index) => (
                    <tr key={index}>
                      <td>{index + 1}</td>
                      <td>{item.filename}</td>
                      <td>{item.similarity}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    );
  }
  if (page === "report" && result) {
    return (
      <div className="page">
        <div className="container">
          <div className="report-header">
          <button className="back-button" onClick={() => setPage("main")}>
            ← Назад
          </button>
          <button className="export-button" onClick={exportReportToPDF}>
            Експорт у PDF
          </button>
          </div>

          <div className="report-page">
            <h1>Звіт про перевірку тексту</h1>

            <div className="report-grid">
              <div className="report-column">
                <div className="report-section">
                  <h2>Загальний результат</h2>

                  <p>
                    <b>Найбільш схожий документ:</b> {result.most_similar_file}
                  </p>

                  <p>
                    <b>Максимальна схожість:</b> {result.similarity}%
                  </p>

                  <p>
                    <b>Унікальність тексту:</b> {result.uniqueness}%
                  </p>

                  <p>
                    <b>Стиль тексту:</b> {result.text_style}
                  </p>
                </div>


                {result.mode === "plagiarism" && (
                  <div className="report-section">
                    <h2>Спільні слова</h2>

                    <div className="words">
                      {result.common_words.length > 0 ? (
                        result.common_words.map((item, index) => (
                          <span
                            key={index}
                            className="common-word"
                            onMouseEnter={() =>
                              setHoveredWord({
                                input: item.input_positions,
                                similar: item.similar_positions
                              })
                            }
                            onMouseLeave={() => setHoveredWord(null)}
                          >
                            {item.word} ({item.count})
                          </span>
                        ))
                      ) : (
                        <p>Спільних слів не знайдено.</p>
                      )}
                    </div>
                  </div>
                )}

                <div className="report-section">
                  <h2>Вхідний текст</h2>
                    <div className="text-box">
                      {highlightText(result.input_text, hoveredWord?.input)}
                    </div>
                  </div>
                </div>

                <div className="report-column">
                  <div className="report-section">
                    <h2>Найбільш схожий текст</h2>
                    <div className="text-box">
                      {highlightText(result.most_similar_text, hoveredWord?.similar)}
                    </div>
                  </div>

                  <div className="report-section">
                    <h2>10 найбільш схожих текстів</h2>

                    <table>
                      <thead>
                        <tr>
                          <th>№</th>
                          <th>Назва файлу</th>
                          <th>Схожість</th>
                        </tr>
                      </thead>

                      <tbody>
                        {result.top_results.map((item, index) => (
                          <tr key={index}>
                            <td>{index + 1}</td>

                            <td>
                              {item.filename}
                            </td>

                            <td>{item.similarity}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>

                    <button
                      className="report-button"
                      onClick={() => setPage("allResults")}
                    >
                      Показати всі результати
                    </button>

                  </div>

                  <div className="report-section">
                    <h2>Діаграма схожості</h2>

                    <PieChart width={600} height={400}>
                      <Pie
                        data={result.top_results.map((item, index) => ({
                          ...item,
                          fill: getColor(index)
                        }))}
                        dataKey="similarity"
                        nameKey="filename"
                        cx="50%"
                        cy="50%"
                        outerRadius={120}
                        label={({ percent }) => `${(percent * 100).toFixed(1)}%`}
                      />

                      <Tooltip formatter={(value) => `${value}%`} />
                      <Legend />
                    </PieChart>
                  </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }
  return (
    <div className="page">
      <div className="container">
        <h1>Система перевірки тексту</h1>

        <div className="card">
          <label>Спосіб введення:</label>

          <select
            value={inputType}
            onChange={(e) => {
              setInputType(e.target.value);
              setText("");
              setFile(null);
            }}
          >
            <option value="text">Ввести текст</option>
            <option value="file">Завантажити файл</option>
          </select>

          {inputType === "text" && (
            <>
              <label>Введіть текст:</label>

              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Вставте текст..."
              />
            </>
          )}

          {inputType === "file" && (
            <>
              <label>Завантажте файл:</label>

              <input
                type="file"
                accept=".pdf,.docx,.odt"
                onChange={(e) => setFile(e.target.files[0])}
              />
            </>
          )}

          <br />

          <label>Тип перевірки:</label>

          <select value={mode} onChange={(e) => setMode(e.target.value)}>
            <option value="plagiarism">Перевірка на плагіат</option>
            <option value="semantic">Семантична схожість</option>
          </select>

          {mode === "plagiarism" && (
            <>
              <label>Оберіть n-граму:</label>

              <select value={ngramN} onChange={(e) => setNgramN(e.target.value)}>
                <option value={2}>2</option>
                <option value={3}>3</option>
                <option value={4}>4</option>
              </select>
            </>
          )}

          <button onClick={checkText} disabled={loading}>
            {loading ? "Обробка..." : "Перевірити"}
          </button>
          {loading && (
            <div className="loading-box">
              <div className="spinner"></div>

              <p>Триває обробка тексту...</p>

              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${progress}%` }}
                ></div>
              </div>

              <span>{progress}%</span>
            </div>
          )}

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

            <button className="report-button" onClick={() => setPage("report")}>
              Переглянути звіт
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;