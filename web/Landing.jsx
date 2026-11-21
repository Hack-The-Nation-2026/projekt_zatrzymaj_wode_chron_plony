import React, { useState } from "react";
import { api } from "./api.js";
import "./landing.css";

// Strona startowa: opis projektu, pitch, model biznesowy oraz logowanie i zakładanie konta.
// onAuth(user) – po zalogowaniu / rejestracji; onGuest() – „Wypróbuj bez konta”.

const STATS = [
  { num: "4,36 mld zł", desc: "wypłaciła ARiMR w programach pomocy po suszach 2018–2019", src: "NIK, P/21/048" },
  { num: "7,5%", desc: "średniorocznego odpływu zatrzymuje Polska w zbiornikach, choć mogłaby ok. 15%", src: "NIK, gov.pl/web/retencja" },
  { num: "ok. 1600 m³", desc: "wody na mieszkańca rocznie: jeden z najniższych wyników w UE", src: "GUS, raport SDG" },
  { num: "1,32 mln", desc: "gospodarstw rolnych, średnio 12,4 ha: każde z innym polem i inną glebą", src: "GUS, PSR 2020" },
];

const STEPS = [
  { n: 1, t: "Ocena", d: "Czy na tej działce i w tym dniu roślinom brakuje wody?" },
  { n: 2, t: "Przyczyny", d: "Mało deszczu, gleba, która nie trzyma wody, czy spływ z pola?" },
  { n: 3, t: "Retencja", d: "Gdzie dokładnie zatrzymać wodę: wał, zastawka, pas zieleni." },
  { n: 4, t: "Agrotechnika", d: "Międzyplony, resztki pożniwne, uprawa ograniczająca parowanie." },
  { n: 5, t: "Nawadnianie", d: "Na końcu i tylko gdy ma sens: kiedy i ile wody." },
];

const SOURCES = [
  { icon: "parcel", t: "Działka i teren", d: "GUGiK: granice działek i model terenu z lotniczego skanowania laserowego, 1 m." },
  { icon: "water", t: "Rowy i cieki", d: "BDOT10k: rowy, cieki, zbiorniki, mokradła i lasy wokół pola." },
  { icon: "rain", t: "Pogoda", d: "Copernicus ERA5: ostatnie miesiące i 10 lat tła, prognoza na 7 dni." },
  { icon: "sat", t: "Satelita", d: "Sentinel-2: zieloność i uwodnienie roślin, oceniane według uprawy." },
  { icon: "soil", t: "Gleba", d: "ISRIC SoilGrids: ile wody gleba potrafi zatrzymać." },
];

const MODEL = [
  { t: "Dla kogo", d: "Rolnicy bezpłatnie. Doradcy ODR, gminy i spółki wodne jako użytkownicy profesjonalni." },
  { t: "Kanały", d: "KOWR i ośrodki doradztwa rolniczego. Aplikacja w przeglądarce, także na telefonie." },
  { t: "Wartość dla państwa", d: "Mniej strat po suszy i mniej pomocy doraźnej; dotacje na retencję tam, gdzie naprawdę działają." },
  { t: "Koszty", d: "Dane publiczne i otwarte licencje, bez opłat za dane. Główny koszt to hosting i utrzymanie." },
  { t: "Partnerzy", d: "IUNG-PIB, IMGW-PIB, GUGiK, Wody Polskie, CDR w Brwinowie." },
  { t: "Skala", d: "Dane krajowe, więc cała Polska od startu. Dalej: protokół strat suszowych i API dla ARiMR." },
];

function Icon({ name }) {
  const p = { fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round" };
  const paths = {
    parcel: <><path d="M4 7l6-3 6 3 4-2v12l-4 2-6-3-6 3V7z" {...p} /><path d="M10 4v12M16 7v12" {...p} /></>,
    water: <><path d="M3 15c2.5-2 4.5 2 7 0s4.5 2 7 0 3 0 4 0" {...p} /><path d="M3 10c2.5-2 4.5 2 7 0s4.5 2 7 0 3 0 4 0" {...p} /></>,
    rain: <><path d="M7 15a4 4 0 010-8 5 5 0 019.6 1.5A3.5 3.5 0 0117 15H7z" {...p} /><path d="M8 18l-1 2M12 18l-1 2M16 18l-1 2" {...p} /></>,
    sat: <><rect x="9" y="9" width="6" height="6" rx="1" {...p} /><path d="M3 5l4 4M17 15l4 4M9 12H4M20 12h-5M12 9V4M12 20v-5" {...p} /></>,
    soil: <><path d="M3 9h18M3 14h18M3 19h18" {...p} /><path d="M12 9V4M9 6l3-2 3 2" {...p} /></>,
  };
  return <svg width="26" height="26" viewBox="0 0 24 24" aria-hidden="true">{paths[name]}</svg>;
}

function ReportPreview() {
  return (
    <div className="lp-preview" aria-label="Przykładowy fragment raportu">
      <div className="lp-preview-label">Tak wygląda raport</div>
      <div className="lp-preview-head">
        <span>Łazisko · pszenica ozima · 15.06.2026</span>
        <span className="lp-chip warn">Rośliny w stresie wodnym</span>
      </div>
      <svg viewBox="0 0 300 90" className="lp-preview-chart" aria-hidden="true">
        <rect x="0" y="48" width="300" height="42" fill="#3a1f24" opacity="0.5" />
        <line x1="0" x2="300" y1="48" y2="48" stroke="#ff8a80" strokeDasharray="4 4" />
        <polyline points="0,8 40,9 80,14 120,22 150,40 175,62 200,78 225,80 240,72 250,66" fill="none" stroke="#4aa3e8" strokeWidth="2.5" />
        <polygon points="250,66 275,58 300,50 300,82 275,80 250,66" fill="#4aa3e8" opacity="0.25" />
        <line x1="250" x2="250" y1="0" y2="90" stroke="#f4f7f9" strokeWidth="1" />
      </svg>
      <ol className="lp-preview-recs">
        <li>Wał 30 cm w punktach odpływu: ok. 433 m zatrzyma ulewę 50 mm</li>
        <li>Oczko w naturalnym obniżeniu: zmieści ok. 781 m³ wody</li>
        <li>Międzyplony i resztki pożniwne: +5 mm wody w glebie</li>
      </ol>
    </div>
  );
}

function AuthCard({ onAuth, onGuest }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const user = mode === "login"
        ? await api.login({ email, password })
        : await api.register({ email, password, name });
      onAuth(user);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="lp-auth" id="logowanie">
      <div className="lp-tabs" role="tablist">
        <button type="button" role="tab" aria-selected={mode === "login"} className={mode === "login" ? "on" : ""}
                onClick={() => { setMode("login"); setError(""); }}>Logowanie</button>
        <button type="button" role="tab" aria-selected={mode === "register"} className={mode === "register" ? "on" : ""}
                onClick={() => { setMode("register"); setError(""); }}>Załóż konto</button>
      </div>
      <form onSubmit={submit}>
        {mode === "register" && (
          <>
            <label htmlFor="lp-name">Imię (opcjonalnie)</label>
            <input id="lp-name" autoComplete="given-name" value={name} onChange={(e) => setName(e.target.value)} />
          </>
        )}
        <label htmlFor="lp-email">E-mail</label>
        <input id="lp-email" type="email" required autoComplete="email" value={email}
               onChange={(e) => setEmail(e.target.value)} />
        <label htmlFor="lp-pass">Hasło</label>
        <input id="lp-pass" type="password" required minLength={mode === "register" ? 8 : undefined}
               autoComplete={mode === "login" ? "current-password" : "new-password"} value={password}
               onChange={(e) => setPassword(e.target.value)} />
        {mode === "register" && <p className="lp-hint">Co najmniej 8 znaków. Konto zapisuje historię Twoich raportów.</p>}
        {error && <p className="error-msg" role="alert">{error}</p>}
        <button className="btn dark lp-submit" disabled={busy}>
          {busy ? "Chwila…" : mode === "login" ? "Zaloguj się" : "Załóż konto"}
        </button>
      </form>
      <button type="button" className="lp-guest" onClick={onGuest}>Wypróbuj bez konta →</button>
    </div>
  );
}

export default function Landing({ onAuth, onGuest }) {
  return (
    <div className="lp">
      <nav className="lp-nav">
        <div className="lp-logo">
          <svg width="22" height="28" viewBox="0 0 22 28" aria-hidden="true">
            <path d="M11 1C11 1 1 14 1 19a10 10 0 0020 0C21 14 11 1 11 1z" fill="#4aa3e8" />
          </svg>
          Wodnik
        </div>
        <div className="lp-links">
          <a href="#jak">Jak to działa</a>
          <a href="#dane">Dane</a>
          <a href="#model">Model</a>
          <a className="btn dark lp-nav-btn" href="#logowanie">Zaloguj się</a>
        </div>
      </nav>

      <header className="lp-hero">
        <div className="lp-hero-text">
          <div className="eyebrow">HackNation 2026 · zadanie KOWR</div>
          <h1>Zatrzymaj wodę,<br />chroń plony</h1>
          <p className="lp-lead">
            Wpisz numer działki i datę. Wodnik sprawdzi, czy Twoim roślinom brakuje wody, wyjaśni dlaczego
            i wskaże, gdzie na polu ją zatrzymać. Na danych publicznych, za darmo, w kilka minut.
          </p>
          <div className="lp-cta">
            <a className="btn dark" href="#logowanie">Załóż darmowe konto</a>
            <button type="button" className="btn" onClick={onGuest}>Sprawdź działkę bez konta</button>
          </div>
          <ReportPreview />
        </div>
        <AuthCard onAuth={onAuth} onGuest={onGuest} />
      </header>

      <section className="lp-section">
        <div className="eyebrow">Problem</div>
        <h2 className="lp-h2">Za suszę płacimy po fakcie</h2>
        <div className="lp-stats">
          {STATS.map((s) => (
            <div className="lp-stat" key={s.num}>
              <b>{s.num}</b>
              <span>{s.desc}</span>
              <small>{s.src}</small>
            </div>
          ))}
        </div>
      </section>

      <section className="lp-section lp-pitch">
        <div>
          <div className="eyebrow">Dlaczego Wodnik</div>
          <h2 className="lp-h2">Rolnik zna swoje pole. My dokładamy dane.</h2>
          <p>
            Bardzo szanujemy pracę rolników: to oni najlepiej znają swoją ziemię, uprawy i pogodę za oknem.
            Łączenie zdjęć satelitarnych, modeli terenu i wieloletnich danych pogodowych to jednak zupełnie inna
            specjalizacja, która nie powinna spadać na barki gospodarstwa. Wodnik robi to za rolnika i zamienia dane
            w konkretne wskazówki dla jednego pola.
          </p>
          <p>
            Pomoc suszowa przychodzi po stracie. Wodnik ma pomóc wcześniej: pokazać, gdzie woda ucieka z pola,
            co zatrzyma ją najtaniej i jakie jest ryzyko w najbliższych 30 dniach.
          </p>
        </div>
        <figure className="lp-photo">
          <img src="/img/rolnik-pole.jpg" alt="Rolnik na skraju pola pszenicy o zachodzie słońca sprawdza w telefonie mapę swojej działki"
               loading="lazy" width="1600" height="900" />
          <figcaption>Wodnik działa w telefonie, prosto z pola.</figcaption>
        </figure>
      </section>

      <section className="lp-section" id="jak">
        <div className="eyebrow">Jak to działa</div>
        <h2 className="lp-h2">Od diagnozy do działania w 5 krokach</h2>
        <div className="lp-steps">
          {STEPS.map((s) => (
            <div className={`lp-step${s.n === 5 ? " last" : ""}`} key={s.n}>
              <span className="lp-step-n">{s.n}</span>
              <h3>{s.t}</h3>
              <p>{s.d}</p>
            </div>
          ))}
        </div>
        <p className="lp-note">
          Kolejność zgodna z wytycznymi KOWR: retencja zawsze przed nawadnianiem. Do tego scenariusze na 30 dni,
          wykresy, raport do druku i asystent, który odpowie na pytania o raport.
        </p>
      </section>

      <section className="lp-section" id="dane">
        <div className="eyebrow">Dane</div>
        <h2 className="lp-h2">Pięć źródeł danych publicznych, liczonych od nowa dla każdej działki</h2>
        <div className="lp-sources">
          {SOURCES.map((s) => (
            <div className="lp-source" key={s.t}>
              <span className="lp-source-icon"><Icon name={s.icon} /></span>
              <h3>{s.t}</h3>
              <p>{s.d}</p>
            </div>
          ))}
        </div>
        <p className="lp-note">Każda rada ma źródło i poziom pewności. Wyniki liczą jawne reguły naukowe (FAO-56, metodyka IUNG), a brak danych mówimy wprost.</p>
      </section>

      <section className="lp-section" id="model">
        <div className="eyebrow">Model biznesowy</div>
        <h2 className="lp-h2">Darmowe dla rolnika, opłacalne dla państwa</h2>
        <div className="lp-model">
          {MODEL.map((m) => (
            <div className="lp-model-card" key={m.t}>
              <h3>{m.t}</h3>
              <p>{m.d}</p>
            </div>
          ))}
        </div>
        <div className="lp-roadmap">
          <div><b>Dziś</b><span>Prototyp: dowolna działka w Polsce, data z 10 lat, raport i asystent.</span></div>
          <div><b>3 miesiące</b><span>Pilotaż w jednym województwie z doradcami ODR i walidacja z IUNG.</span></div>
          <div><b>12 miesięcy</b><span>Cała Polska, wynik w kilka sekund, integracja z systemami KOWR i ARiMR.</span></div>
        </div>
      </section>

      <section className="lp-final">
        <h2 className="lp-h2">Sprawdź swoją działkę</h2>
        <p>Konto jest bezpłatne i zapisuje historię raportów. Możesz też zacząć bez konta.</p>
        <div className="lp-cta" style={{ justifyContent: "center" }}>
          <a className="btn dark" href="#logowanie">Zaloguj się lub załóż konto</a>
          <button type="button" className="btn" onClick={onGuest}>Wypróbuj bez konta</button>
        </div>
      </section>

      <footer className="lp-foot">
        Prototyp HackNation 2026 · zadanie KOWR „Zatrzymaj wodę, chroń plony” · dane: GUGiK, Copernicus (ERA5, Sentinel-2),
        ISRIC SoilGrids, Open-Meteo. Zalecenia wymagają sprawdzenia w terenie i nie zastępują porady doradcy rolniczego.
      </footer>
    </div>
  );
}
