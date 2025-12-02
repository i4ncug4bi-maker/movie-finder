import os
import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request, abort

# ---------------------------------------------------
# CONFIG & TMDB
# ---------------------------------------------------

# Încarcă variabilele din .env (local).
load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
if not TMDB_API_KEY:
    raise RuntimeError("TMDB_API_KEY nu este setat în .env sau environment!")

app = Flask(__name__)

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w342"  # pentru postere

# Regiuni suportate (EU + US)
REGIONS = [
    ("IE", "Ireland"),
    ("RO", "Romania"),
    ("US", "United States"),
    ("UK", "United Kingdom"),
    ("ES", "Spain"),
    ("FR", "France"),
    ("DE", "Germany"),
    ("PL", "Poland"),
    ("SE", "Sweden"),
    ("DK", "Denmark"),
    ("FI", "Finland"),
    ("PT", "Portugal"),
    ("AT", "Austria"),
    ("CZ", "Czech Republic"),
    ("HU", "Hungary"),
    ("GR", "Greece"),
    ("BG", "Bulgaria"),
]

DEFAULT_REGION = "IE"   # aici poți schimba regiunea implicită


def tmdb_get(path, params=None):
    """Apel simplu la TMDB."""
    if params is None:
        params = {}

    params["api_key"] = TMDB_API_KEY
    params.setdefault("language", "en-US")

    resp = requests.get(f"{TMDB_BASE_URL}{path}", params=params, timeout=10)
    if resp.status_code == 200:
        return resp.json()

    print("TMDB error:", resp.status_code, resp.text)
    return {}


# ---------------------------------------------------
# LOGICĂ TMDB
# ---------------------------------------------------

def get_genres():
    data = tmdb_get("/genre/movie/list")
    return data.get("genres", [])


def search_movies(title=None, genre_id=None, year=None):
    """Search endpoint logic."""
    if title:
        params = {"query": title, "include_adult": False}
        if year:
            params["year"] = year

        data = tmdb_get("/search/movie", params)
        results = data.get("results", [])

        if genre_id:
            results = [m for m in results if genre_id in m.get("genre_ids", [])]
    else:
        params = {"sort_by": "popularity.desc", "include_adult": False}
        if genre_id:
            params["with_genres"] = genre_id
        if year:
            params["primary_release_year"] = year

        data = tmdb_get("/discover/movie", params)
        results = data.get("results", [])

    return results


def get_movie_details(movie_id, region=DEFAULT_REGION):
    """Detalii film + trailer + where to watch (în funcție de regiune)."""

    data = tmdb_get(
        f"/movie/{movie_id}",
        params={"append_to_response": "videos,watch/providers"},
    )

    if not data or "id" not in data:
        return None

    # Trailer YouTube
    trailer_url = None
    videos = data.get("videos", {}).get("results", [])
    for v in videos:
        if v.get("site") == "YouTube" and v.get("type") == "Trailer":
            key = v.get("key")
            if key:
                trailer_url = f"https://www.youtube.com/watch?v={key}"
                break

    # Where to watch (providers)
    providers_root = data.get("watch/providers", {}).get("results", {})
    region_info = providers_root.get(region, {}) if isinstance(providers_root, dict) else {}

    flatrate = region_info.get("flatrate", []) or []
    buy = region_info.get("buy", []) or []
    rent = region_info.get("rent", []) or []

    # extract provider names
    def provider_names(group):
        return [p.get("provider_name") for p in group if p.get("provider_name")]

    where_to_watch = {
        "stream": provider_names(flatrate),
        "buy": provider_names(buy),
        "rent": provider_names(rent),
    }

    movie = {
        "id": data["id"],
        "title": data.get("title"),
        "overview": data.get("overview"),
        "poster_url": TMDB_IMAGE_BASE + data["poster_path"]
        if data.get("poster_path") else None,
        "year": (data.get("release_date") or "")[:4],
        "rating": (
            round(data.get("vote_average"), 1)
            if data.get("vote_average") is not None
            else None
        ),
        "votes": data.get("vote_count"),
        "genres": [g["name"] for g in data.get("genres", [])],
        "trailer_url": trailer_url,
        "where_to_watch": where_to_watch,
        "region": region,
    }

    return movie


# ---------------------------------------------------
# ROUTE-URI FLASK
# ---------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    genres = get_genres()
    return render_template("index.html", genres=genres)


@app.route("/search", methods=["POST"])
def search():
    title = (request.form.get("title") or "").strip()
    genre_id_raw = request.form.get("genre_id") or ""
    year_raw = (request.form.get("year") or "").strip()

    genre_id = int(genre_id_raw) if genre_id_raw.isdigit() else None
    year = int(year_raw) if year_raw.isdigit() else None

    genres = get_genres()
    genre_name = None
    if genre_id:
        for g in genres:
            if g["id"] == genre_id:
                genre_name = g["name"]
                break

    tmdb_results = search_movies(title=title or None, genre_id=genre_id, year=year)

    movies = []
    for m in tmdb_results:
        poster_url = (
            TMDB_IMAGE_BASE + m["poster_path"] if m.get("poster_path") else None
        )
        movies.append({
            "id": m["id"],
            "title": m.get("title"),
            "overview": (m.get("overview") or "")[:230],
            "poster_url": poster_url,
            "rating": round(m.get("vote_average"), 1)
            if m.get("vote_average") is not None else None,
            "votes": m.get("vote_count"),
            "year": (m.get("release_date") or "")[:4],
        })

    return render_template(
        "results.html",
        movies=movies,
        title_query=title,
        genre_name=genre_name,
        year=year,
    )


@app.route("/movie/<int:movie_id>")
def movie_detail(movie_id):
    # luăm regiunea din query string ex: /movie/123?region=RO
    region = request.args.get("region", DEFAULT_REGION)

    # validăm regiunea
    valid_codes = {code for code, _ in REGIONS}
    if region not in valid_codes:
        region = DEFAULT_REGION

    movie = get_movie_details(movie_id, region=region)
    if not movie:
        abort(404)

    return render_template(
        "detail.html",
        movie=movie,
        region=region,
        regions=REGIONS,
    )


if __name__ == "__main__":
    app.run(debug=True)