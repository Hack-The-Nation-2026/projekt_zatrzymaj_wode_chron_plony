export const theme = {
  // Paleta serwisu (web/styles.css, web/landing.css, web/charts.js): granat nocy,
  // woda z wykresów, zieleń uprawy i złoto zboża z obrysu działki.
  deep: '#0e1d2a', // tło aplikacji
  night: '#09141e', // pasek górny
  panel: '#132535', // karta
  card: '#0c1924', // karta wewnętrzna
  line: '#22394d', // obramowania i siatka wykresów
  water: '#4aa3e8', // woda: akcent i fala kliknięcia
  waterDeep: '#1d5f9a', // linia zapasu wody
  green: '#63b34e', // akcent uprawy (eyebrow, nagłówki)
  greenDark: '#4d8b3c', // przycisk główny
  gold: '#e8b13a', // złoto zboża: granica działki
  warn: '#fbbf24', // ryzyko umiarkowane
  alert: '#ff8a80', // ryzyko wysokie i próg stresu
  ink: '#f4f7f9', // tekst główny
  muted: '#9db0c0', // tekst pomocniczy
  soft: '#c7d5e0', // akapity
  paper: '#0e1d2a', // tło pod nagraniem (ta sama barwa co aplikacja)
  font: '"IBM Plex Sans", system-ui, sans-serif',
}

export const ease = {
  // Jedna krzywa dla całego filmu, żeby ruch był spójny.
  smooth: (value: number) => 1 - Math.pow(1 - value, 3),
  inOut: (value: number) => (value < 0.5 ? 4 * value ** 3 : 1 - Math.pow(-2 * value + 2, 3) / 2),
}
