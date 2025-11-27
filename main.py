import os
from dotenv import load_dotenv
import requests
from flask import Flask, render_template, request

# ============================
#   CONFIG & INITIAL SETUP
# ============================

load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
BASE_URL = "https://api.themoviedb.org/3"

app = Flask(__name__)


# ============================
#       HELPER FUNCTIONS
# ============================

def get_genres():
    """Return list of movie genres from TMDB."""
    url = f"{BASE_URL}/genre/movie/list"
    params = {
        "api_key": TMDB_API_KEY,
        "language": "en-US",
    }

    try:
        resp = requests.get(url, params=params, timeout=10, verify=False)
        if resp.status_code == 200:
            return resp.json().get("genres", [])
        print("TMDB error (genres):", resp.status_code)
    except requests.exceptions.RequestException as e:
        print("SSL / Network error at get_genres():", e)

    return []


def discover_movies(genre_id=None, year=None):
    """Discover popular movies, optionally filtered by genre and year."""
    url = f"{BASE_URL}/discover/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "language": "en-US",
        "sort_by": "popularity.desc",
    }
    if genre_id:
        params["with_genres"] = genre_id
    if year:
        params["primary_release_year"] = year

    try:
        resp = requests.get(url, params=params, timeout=10, verify=False)
        if resp.status_code == 200:
            return resp.json().get("results", [])
        print("TMDB error (discover):", resp.status_code)
    except requests.exceptions.RequestException as e:
        print("SSL / Network error at discover_movies():", e)

    return []


def search_movies(query=None, genre_id=None, year=None):
    """
    Search movies by title (+ optional genre/year).
    If no title is given, fallback to discover_movies().
    """
    if query:
        url = f"{BASE_URL}/search/movie"
        params = {
            "api_key": TMDB_API_KEY,
            "language": "en-US",
            "query": query,
            "include_adult": "false",
        }
        if genre_id:
            params["with_genres"] = genre_id
        if year:
            params["primary_release_year"] = year
    else:
        return discover_movies(genre_id, year)

    try:
        resp = requests.get(url, params=params, timeout=10, verify=False)
        if resp.status_code == 200:
            return resp.json().get("results", [])
        print("TMDB error (search):", resp.status_code)
    except requests.exceptions.RequestException as e:
        print("SSL / Network error at search_movies():", e)

    return []


def get_movie_details(movie_id: int):
    """Get full movie details from TMDB."""
    url = f"{BASE_URL}/movie/{movie_id}"
    params = {
        "api_key": TMDB_API_KEY,
        "language": "en-US",
    }

    try:
        resp = requests.get(url, params=params, timeout=10, verify=False)
        if resp.status_code == 200:
            return resp.json()
        print("TMDB error (details):", resp.status_code)
    except requests.exceptions.RequestException as e:
        print("SSL / Network error at get_movie_details():", e)

    return None


def get_movie_trailer(movie_id: int):
    """Return YouTube trailer URL if available."""
    url = f"{BASE_URL}/movie/{movie_id}/videos"
    params = {
        "api_key": TMDB_API_KEY,
        "language": "en-US",
    }

    try:
        resp = requests.get(url, params=params, timeout=10, verify=False)
        if resp.status_code == 200:
            videos = resp.json().get("results", [])
            for v in videos:
                if v.get("site") == "YouTube" and v.get("type") == "Trailer":
                    key = v.get("key")
                    if key:
                        return f"https://www.youtube.com/watch?v={key}"
        print("TMDB error (trailer):", resp.status_code)
    except requests.exceptions.RequestException as e:
        print("SSL / Network error at get_movie_trailer():", e)

    return None


def get_watch_providers(movie_id: int, region: str = "IE"):
    """Return streaming providers list for a movie (flatrate/rent/buy)."""
    url = f"{BASE_URL}/movie/{movie_id}/watch/providers"
    params = {"api_key": TMDB_API_KEY}

    try:
        resp = requests.get(url, params=params, timeout=10, verify=False)
        if resp.status_code == 200:
            results = resp.json().get("results", {})
            region_data = results.get(region) or results.get("US")
            if not region_data:
                return []

            providers = []
            for kind in ("flatrate", "rent", "buy"):
                for p in region_data.get(kind, []):
                    providers.append(
                        {
                            "name": p.get("provider_name"),
                            "type": kind,
                        }
                    )
            return providers

        print("TMDB error (providers):", resp.status_code)
    except requests.exceptions.RequestException as e:
        print("SSL / Network error at get_watch_providers():", e)

    return []


def get_similar_movies(movie_id: int):
    """Return a short list of similar movies (for recommendations)."""
    url = f"{BASE_URL}/movie/{movie_id}/similar"
    params = {
        "api_key": TMDB_API_KEY,
        "language": "en-US",
    }

    try:
        resp = requests.get(url, params=params, timeout=10, verify=False)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            similar = []
            for m in results[:8]:  # max 8 recomandări
                similar.append({
                    "id": m.get("id"),
                    "title": m.get("title"),
                    "poster_path": m.get("poster_path"),
                    "vote_average": m.get("vote_average"),
                    "release_date": m.get("release_date", "")
                })
            return similar
        print("TMDB error (similar):", resp.status_code)
    except requests.exceptions.RequestException as e:
        print("SSL / Network error at get_similar_movies():", e)

    return []


# ============================
#          ROUTES
# ============================

@app.route("/", methods=["GET"])
def index():
    genres = get_genres()
    return render_template("index.html", genres=genres)


@app.route("/search", methods=["POST"])
def search():
    query = request.form.get("query", "").strip()
    genre_id = request.form.get("genre", "").strip()
    year = request.form.get("year", "").strip()

    genres = get_genres()

    if not query and not genre_id and not year:
        movies = discover_movies()
    else:
        movies = search_movies(
            query if query else None,
            genre_id if genre_id else None,
            year if year else None,
        )

    return render_template(
        "results.html",
        movies=movies,
        genres=genres,
        query=query,
        selected_genre=genre_id,
        selected_year=year,
    )


@app.route("/movie/<int:movie_id>")
def movie_detail(movie_id):
    """Movie details page."""
    movie = get_movie_details(movie_id)
    if not movie:
        return "Movie not found", 404

    trailer_url = get_movie_trailer(movie_id)
    providers = get_watch_providers(movie_id)
    similar = get_similar_movies(movie_id)

    return render_template(
        "detail.html",
        movie=movie,
        trailer_url=trailer_url,
        providers=providers,
        similar_movies=similar,
    )


# ============================
#          RUN APP
# ============================

if __name__ == "__main__":
    app.run(debug=True)
