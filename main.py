from flask import Flask, render_template, request
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

TMDB_API_KEY = os.getenv("TMDB_API_KEY")

# lista de genuri (TMDB IDs)
GENRES = [
    {"id": "", "name": "Any genre"},
    {"id": "28", "name": "Action"},
    {"id": "12", "name": "Adventure"},
    {"id": "16", "name": "Animation"},
    {"id": "35", "name": "Comedy"},
    {"id": "80", "name": "Crime"},
    {"id": "18", "name": "Drama"},
    {"id": "14", "name": "Fantasy"},
    {"id": "27", "name": "Horror"},
    {"id": "10749", "name": "Romance"},
    {"id": "878", "name": "Science Fiction"},
    {"id": "53", "name": "Thriller"},
]


@app.route("/", methods=["GET", "POST"])
def home():
    movies = []
    error = None

    if request.method == "POST":
        query = request.form.get("query", "").strip()
        genre_id = request.form.get("genre", "")
        year = request.form.get("year", "").strip()

        if not TMDB_API_KEY:
            error = "TMDB API key is missing. Check your .env file."
        else:
            # dacă utilizatorul scrie un titlu, folosim /search
            if query:
                url = "https://api.themoviedb.org/3/search/movie"
                params = {
                    "api_key": TMDB_API_KEY,
                    "language": "en-US",
                    "query": query,
                    "include_adult": "false",
                }
            else:
                # dacă nu scrie titlu, folosim /discover cu filtre
                url = "https://api.themoviedb.org/3/discover/movie"
                params = {
                    "api_key": TMDB_API_KEY,
                    "language": "en-US",
                    "include_adult": "false",
                    "sort_by": "popularity.desc",
                }

            if genre_id:
                params["with_genres"] = genre_id
            if year:
                params["primary_release_year"] = year

            try:
                resp = requests.get(url, params=params, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                movies = data.get("results", [])
            except Exception as e:
                error = f"Something went wrong while talking to TMDB: {e}"

    return render_template("index.html", movies=movies, genres=GENRES, error=error)


@app.route("/movie/<int:movie_id>")
def movie_detail(movie_id):
    movie = None
    trailer_key = None

    if not TMDB_API_KEY:
        return "TMDB API key is missing. Check your .env file."

    base_params = {"api_key": TMDB_API_KEY, "language": "en-US"}

    # detalii film
    detail_resp = requests.get(
        f"https://api.themoviedb.org/3/movie/{movie_id}",
        params=base_params,
        timeout=10,
    )
    if detail_resp.status_code == 200:
        movie = detail_resp.json()

    # trailere (YouTube)
    videos_resp = requests.get(
        f"https://api.themoviedb.org/3/movie/{movie_id}/videos",
        params=base_params,
        timeout=10,
    )
    if videos_resp.status_code == 200:
        for v in videos_resp.json().get("results", []):
            if v.get("site") == "YouTube" and v.get("type") == "Trailer":
                trailer_key = v.get("key")
                break

    return render_template("detail.html", movie=movie, trailer_key=trailer_key)


if __name__ == "__main__":
    app.run(debug=True)
