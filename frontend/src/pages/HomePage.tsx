import { Link } from "react-router-dom";
import { Mascot } from "../components/Mascot";

export function HomePage() {
  return (
    <div>
      <section className="home-hero">
        <div className="home-hero-inner">
          <h1 className="home-hero-title">
            Спутник
            <br />
            Самарского
          </h1>
          <p className="home-hero-subtitle">
            Курсы для студентов
            <br />
            Самарского университета
          </p>
        </div>
      </section>

      <section className="home-body">
        <div className="home-body-inner">
          <Mascot />

          <div className="home-speech-col">
            <div className="speech-bubble">
              Привет! Я — Спутник, твой личный помощник на орбите знаний Самарского университета.
              Здесь, чтобы ты легко прошел курсы, сдал всё на отлично и стал умнее.{" "}
              <strong>Готов к запуску?</strong>
            </div>

            <Link to="/courses" className="btn-pill-cta">
              <span>Посмотреть курсы</span>
              <span aria-hidden="true">→</span>
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}