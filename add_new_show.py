import os
import re
import json
import urllib.request
import urllib.parse

# Klucz API do serwisu The Movie Database (TMDB)
# Możesz wpisać go tutaj na stałe lub ustawić jako zmienną środowiskową TMDB_API_KEY
TMDB_API_KEY = ""

# Mapowanie angielskich gatunków z TVMaze na polskie odpowiedniki
GENRE_MAP = {
    "Drama": "Dramat",
    "Comedy": "Komedia",
    "Action": "Akcja",
    "Science-Fiction": "Sci-Fi",
    "Sci-Fi": "Sci-Fi",
    "Thriller": "Thriller",
    "Mystery": "Mystery",
    "Crime": "Kryminał",
    "Adventure": "Przygodowy",
    "History": "Historyczny",
    "Romance": "Romans",
    "War": "Wojenny",
    "Horror": "Horror",
    "Western": "Western",
    "Music": "Muzyczny",
    "Family": "Familijny",
    "Supernatural": "Fantasy",
    "Fantasy": "Fantasy",
    "Biography": "Biograficzny",
    "Espionage": "Szpiegowski",
    "Legal": "Prawniczy",
    "Medical": "Medyczny"
}

# Mapowanie statusów z TVMaze na polskie odpowiedniki
STATUS_MAP = {
    "Ended": "Zakończony",
    "Canceled": "Anulowany",
    "Running": "W trakcie emisji",
    "In Development": "W trakcie emisji",
    "To Be Determined": "W trakcie emisji"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
}

def get_tmdb_api_key():
    return TMDB_API_KEY or os.environ.get("TMDB_API_KEY")

def translate_genres(genres_list):
    if not genres_list:
        return "Brak gatunku"
    pl_genres = [GENRE_MAP.get(g, g) for g in genres_list]
    return ", ".join(pl_genres)

def translate_status(status_str):
    return STATUS_MAP.get(status_str, "Zakończony")

def plural_seasons(n):
    if n == 1:
        return "1 sezon"
    elif 2 <= n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20):
        return f"{n} sezony"
    else:
        return f"{n} sezonów"

def plural_episodes(n):
    if n == 1:
        return "1 odcinek"
    elif 2 <= n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20):
        return f"{n} odcinki"
    else:
        return f"{n} odcinków"

def translate_text(text, sl="en", tl="pl"):
    if not text:
        return ""
    clean_text = re.sub(r'<[^>]+>', '', text).strip()
    encoded_text = urllib.parse.quote(clean_text)
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={sl}&tl={tl}&dt=t&q={encoded_text}"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode('utf-8'))
        translated = "".join([part[0] for part in res[0] if part and part[0]])
        return translated
    except Exception as e:
        return clean_text

def find_show(title, year):
    query = urllib.parse.quote(title)
    url = f"https://api.tvmaze.com/search/shows?q={query}"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req) as response:
            results = json.loads(response.read().decode('utf-8'))
        if not results:
            return None
        for item in results:
            show = item['show']
            premiered = show.get('premiered')
            if premiered and premiered.startswith(str(year)):
                return show
        return results[0]['show']
    except Exception as e:
        print(f"Błąd wyszukiwania TVMaze dla '{title}': {e}")
        return None

def fetch_embedded_details(show_id):
    url = f"https://api.tvmaze.com/shows/{show_id}?embed[]=seasons&embed[]=episodes"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        return None

def search_tmdb_description(search_titles, year):
    """Szuka opisu serialu w bazie TMDB (najpierw PL, w razie braku – pobiera EN i tłumaczy).
    Obsługuje przekazaną listę tytułów do sprawdzenia po kolei."""
    api_key = get_tmdb_api_key()
    if not api_key:
        return None
    
    if isinstance(search_titles, str):
        titles = [search_titles]
    else:
        titles = search_titles

    for t in titles:
        query = urllib.parse.quote(t)
        # Wyszukiwanie z uwzględnieniem roku premiery
        url = f"https://api.themoviedb.org/3/search/tv?api_key={api_key}&query={query}&first_air_date_year={year}&language=pl-PL"
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req) as response:
                res = json.loads(response.read().decode('utf-8'))
            results = res.get('results', [])
            
            # Próba wyszukania bez filtru roku, jeśli nie znaleziono dopasowania
            if not results:
                url_no_year = f"https://api.themoviedb.org/3/search/tv?api_key={api_key}&query={query}&language=pl-PL"
                req = urllib.request.Request(url_no_year, headers=HEADERS)
                with urllib.request.urlopen(req) as response:
                    res = json.loads(response.read().decode('utf-8'))
                results = res.get('results', [])
                
            if results:
                show = results[0]
                overview = show.get('overview', '').strip()
                if overview:
                    return overview, f"TMDB (PL) [dla '{t}']"
                
                # Jeżeli opis po polsku jest pusty, pobieramy opis po angielsku z detali i go tłumaczymy
                tv_id = show.get('id')
                if tv_id:
                    url_en = f"https://api.themoviedb.org/3/tv/{tv_id}?api_key={api_key}&language=en-US"
                    req_en = urllib.request.Request(url_en, headers=HEADERS)
                    with urllib.request.urlopen(req_en) as response:
                        show_en = json.loads(response.read().decode('utf-8'))
                    overview_en = show_en.get('overview', '').strip()
                    if overview_en:
                        translated = translate_text(overview_en)
                        if translated:
                            return translated, f"TMDB (przetłumaczony z EN) [dla '{t}']"
        except Exception as e:
            print(f"   [Ostrzeżenie] Błąd podczas odpytywania TMDB dla '{t}': {e}")
    return None

def detect_html_file():
    if os.path.exists("index_updated.html"):
        return "index_updated.html"
    elif os.path.exists("index.html"):
        return "index.html"
    return None

def get_next_index(html_content):
    numbers = re.findall(r'<h2 class="card-title">(\d+)\.', html_content)
    if not numbers:
        return 1
    return max(int(n) for n in numbers) + 1

def append_to_html(file_path, card_html):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    grid_end_pattern = r'</div>\s*</main>'
    replacement = f"{card_html}\n</div>\n</main>"
    new_content = re.sub(grid_end_pattern, replacement, content, flags=re.IGNORECASE)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)

def build_search_buttons(query_title):
    encoded_query_plus = urllib.parse.quote_plus(query_title)
    query_lower = query_title.lower()
    encoded_query_upflix = urllib.parse.quote_plus(query_lower)
    encoded_query_filmweb = urllib.parse.quote(query_lower)
    
    return f"""<div class="search-buttons-grid">
<a class="btn-search btn-tmdb" href="https://www.themoviedb.org/search?query={encoded_query_plus}" target="_blank">TMDb</a>
<a class="btn-search btn-imdb" href="https://www.imdb.com/find?q={encoded_query_plus}" target="_blank">IMDb</a>
<a class="btn-search btn-tropes" href="https://tvtropes.org/pmwiki/search_result.php?q={encoded_query_plus}" target="_blank">Tropes</a>
<a class="btn-search btn-filmweb" href="https://www.filmweb.pl/search#/all?query={encoded_query_filmweb}" target="_blank">Filmweb</a>
<a class="btn-search btn-upflix" href="https://upflix.pl/{encoded_query_upflix}" target="_blank">Upflix</a>
</div>"""

def create_card_string(index_num, custom_title, show_year, status_pl, meta_info, genres_pl, description_pl, show_name, ext):
    buttons_html = build_search_buttons(show_name)
    encoded_query_plus = urllib.parse.quote_plus(show_name)
    trailer_url = f"https://www.youtube.com/results?search_query={encoded_query_plus}+{show_year}+Official+Trailer"
    badge_type = "completed" if status_pl == "Zakończony" else "cancelled" if status_pl == "Anulowany" else "ongoing"
    
    return f"""<!-- {index_num}. {custom_title} -->
<article class="card">
<div class="card-image-container">
<img alt="{custom_title}" class="card-image" loading="lazy" src="{index_num}{ext}"/>
</div>
<div class="card-content">
<div class="card-header">
<div class="title-wrapper">
<div>
<h2 class="card-title">{index_num}. {custom_title}</h2>
<span class="years">({show_year})</span>
</div>
<span class="status-badge status-{badge_type}">{status_pl}</span>
</div>
<div class="meta-info">{meta_info}</div>
<div class="genre-info">{genres_pl}</div>
</div>
<p class="description">{description_pl}</p>
</div>
<div class="card-footer">
<a class="btn-trailer" href="{trailer_url}" target="_blank">
<svg viewbox="0 0 24 24"><path d="M8 5v14l11-7z"></path></svg> Zwiastun na YouTube
</a>
{buttons_html}
</div>
</article>"""

def add_single_show(html_file, title, year, is_bulk=False):
    """Przetwarza i dodaje pojedynczy serial na podstawie nazwy i roku."""
    # Obsługa podwójnego tytułu np. "Polska Nazwa / Original Name"
    search_titles = [title]
    if "/" in title:
        parts = [p.strip() for p in title.split("/")]
        if len(parts) >= 2:
            # Pierwsza próba po nazwie oryginalnej (drugi człon), druga po polskiej (pierwszy człon)
            search_titles = [parts[1], parts[0]]

    basic_show = None
    used_title = None
    for t in search_titles:
        basic_show = find_show(t, year)
        if basic_show:
            used_title = t
            break

    if not basic_show:
        print(f"[Błąd] Nie znaleziono serialu dla '{title}' ({year}) w bazie TVMaze.")
        return False
        
    details = fetch_embedded_details(basic_show['id'])
    if not details:
        print(f"[Błąd] Nie udało się pobrać szczegółowych danych dla '{used_title}'.")
        return False
        
    show_name = details.get('name', used_title)
    show_year = details.get('premiered', year)[:4] if details.get('premiered') else year
    status_pl = translate_status(details.get('status', 'Ended'))
    genres_pl = translate_genres(details.get('genres', []))
    
    seasons_list = details.get('_embedded', {}).get('seasons', [])
    episodes_list = details.get('_embedded', {}).get('episodes', [])
    
    seasons_text = plural_seasons(len(seasons_list)) if seasons_list else "Brak danych o sezonach"
    episodes_text = plural_episodes(len(episodes_list)) if episodes_list else ""
    meta_info = f"{seasons_text}, {episodes_text}".strip(", ")
    
    # Przygotowanie opisów ze źródeł
    summary_en = details.get('summary', '')
    description_tvmaze = translate_text(summary_en) if summary_en else ""
    if description_tvmaze:
        description_tvmaze = re.sub(r'<[^>]+>', '', description_tvmaze).strip()

    description_tmdb = None
    tmdb_source = None
    
    # Odpytywanie TMDB (jeśli klucz jest podany) - przekazujemy obie formy tytułu
    if get_tmdb_api_key():
        tmdb_res = search_tmdb_description(search_titles, year)
        if tmdb_res:
            description_tmdb, tmdb_source = tmdb_res
            description_tmdb = re.sub(r'<[^>]+>', '', description_tmdb).strip()
    
    description_pl = ""
    
    if not is_bulk:
        print("\n" + "-"*35)
        print(f"ZNALEZIONO: {show_name} ({show_year})")
        print(f"Status: {status_pl} | Dane: {meta_info}")
        print(f"Gatunki: {genres_pl}")
        print("-"*35)
        
        # Logika wyboru opisu w trybie interaktywnym
        if description_tmdb:
            print(f"\n[1] Znaleziono opis w bazie TMDB ({tmdb_source}):")
            print(f"--------------------------------------------------\n{description_tmdb}\n--------------------------------------------------")
            print("Co chcesz zrobić?")
            print("[1] Zaakceptuj ten opis z TMDB")
            print("[2] Odrzuć i szukaj w bazie TVMaze")
            print("[3] Pozostaw opis pusty")
            
            choice = input("Wybór [1, 2, 3 - Domyślnie: 1]: ").strip()
            if choice == "2":
                if description_tvmaze:
                    print(f"\n[2] Opis z bazy TVMaze (przetłumaczony):")
                    print(f"--------------------------------------------------\n{description_tvmaze}\n--------------------------------------------------")
                    confirm_tvm = input("Czy akceptujesz opis z TVMaze? (T/N - Domyślnie: T): ").strip().lower()
                    if confirm_tvm in ('', 't', 'tak'):
                        description_pl = description_tvmaze
                    else:
                        print("Opis pozostanie pusty.")
                else:
                    print("[!] Brak alternatywnego opisu w TVMaze. Opis pozostanie pusty.")
            elif choice == "3":
                print("Opis pozostanie pusty.")
            else:
                description_pl = description_tmdb
        else:
            # Brak opisu z TMDB - proponujemy TVMaze
            if description_tvmaze:
                print(f"\nZnaleziono opis tylko w bazie TVMaze (przetłumaczony):")
                print(f"--------------------------------------------------\n{description_tvmaze}\n--------------------------------------------------")
                confirm_tvm = input("Czy akceptujesz ten opis? (T/N - Domyślnie: T): ").strip().lower()
                if confirm_tvm in ('', 't', 'tak'):
                    description_pl = description_tvmaze
                else:
                    print("Opis pozostanie pusty.")
            else:
                print("\n[!] Nie odnaleziono opisu w żadnym ze źródeł.")
        
        confirm = input("\nCzy chcesz dodać ten serial? (T/N): ").strip().lower()
        if confirm != 't' and confirm != 'tak':
            print("Pominięto.")
            return False
            
        custom_title = input(f"Wyświetlana nazwa w katalogu [Domyślnie: '{title}']: ").strip()
        if not custom_title:
            custom_title = title
    else:
        # Automatyczny wybór w trybie masowym (zawsze zachowujemy oryginalnie podaną formę z ukośnikiem jako tytuł karty)
        custom_title = title
        print(f"[Masowy] Przetwarzanie: {show_name} ({show_year})...")
        if description_tmdb:
            description_pl = description_tmdb
            print(f"   [Masowy] Wybrano opis z TMDB ({tmdb_source})")
        elif description_tvmaze:
            description_pl = description_tvmaze
            print("   [Masowy] Wybrano opis z TVMaze")
        else:
            print("   [Masowy] Brak opisu we wszystkich źródłach")

    with open(html_file, "r", encoding="utf-8") as f:
        html_content = f.read()
    next_index = get_next_index(html_content)
    
    # Obsługa grafiki plakatowej
    image_url = details.get('image', {}).get('original') or details.get('image', {}).get('medium')
    ext = ".jpg"
    if image_url:
        parsed_path = urllib.parse.urlparse(image_url).path
        detected_ext = os.path.splitext(parsed_path)[1]
        if detected_ext:
            ext = detected_ext
            
        image_path = f"{next_index}{ext}"
        try:
            img_req = urllib.request.Request(image_url, headers=HEADERS)
            with urllib.request.urlopen(img_req) as img_response:
                with open(image_path, "wb") as img_file:
                    img_file.write(img_response.read())
        except Exception as e:
            print(f"   [Ostrzeżenie] Nie pobrano grafiki dla nr {next_index}: {e}")
            
    # Zapis nowej karty w strukturze HTML (używamy show_name do generowania linków wyszukiwania na zewnątrz)
    card_html = create_card_string(next_index, custom_title, show_year, status_pl, meta_info, genres_pl, description_pl, show_name, ext)
    append_to_html(html_file, card_html)
    
    target_img_name = f"{next_index}{ext}"
    print(f"   [Sukces] Dodano pomyślnie jako pozycję nr {next_index} ({target_img_name})")
    return True

def main():
    global TMDB_API_KEY
    html_file = detect_html_file()
    if not html_file:
        print("Błąd: Nie odnaleziono pliku 'index_updated.html' ani 'index.html' w tym folderze!")
        input("\nNaciśnij Enter, aby zamknąć program...")
        return

    print(f"Wykryto plik katalogu: '{html_file}'")
    
    # Sprawdzenie obecności klucza TMDB
    api_key = get_tmdb_api_key()
    if not api_key:
        print("\n[!] Brak skonfigurowanego klucza TMDB_API_KEY.")
        print("Aby móc pobierać opisy z bazy The Movie Database (TMDB), wprowadź klucz.")
        print("Darmowy klucz można wygenerować po rejestracji na stronie https://www.themoviedb.org")
        key_input = input("Wprowadź swój klucz TMDB (lub naciśnij Enter, aby pominąć i używać tylko TVMaze): ").strip()
        if key_input:
            TMDB_API_KEY = key_input
            print("[+] Klucz TMDB został pomyślnie ustawiony na czas trwania tej sesji.")
        else:
            print("[*] Kontynuacja bez TMDB (opisy pobierane będą wyłącznie z bazy TVMaze).")

    print("\nWybierz tryb pracy:")
    print("[1] Interaktywny (ręczne wpisywanie jednego po drugim i potwierdzanie)")
    print("[2] Masowy z pliku (automatyczne pobieranie z listy w pliku 'seriale.txt')")
    
    choice = input("Wybierz tryb [1 lub 2, Domyślnie: 1]: ").strip()
    
    if choice == "2":
        import_file = "seriale.txt"
        if not os.path.exists(import_file):
            with open(import_file, "w", encoding="utf-8") as f:
                f.write("# Wpisz tu seriale w formacie: Tytuł, Rok\n# Przykład:\n# The Bear, 2022\n# Severance, 2022\n")
            print(f"\n[!] Utworzono pusty plik '{import_file}'.")
            print("Wpisz do niego pożądane seriale, zapisz plik i uruchom skrypt ponownie.")
            input("\nNaciśnij Enter, aby zakończyć...")
            return
            
        print(f"\nWczytywanie listy z '{import_file}'...")
        with open(import_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        to_process = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "," in line:
                parts = line.split(",")
                title = ",".join(parts[:-1]).strip()
                year = parts[-1].strip()
                if title and year.isdigit():
                    to_process.append((title, int(year)))
            else:
                match = re.search(r'^(.*?)\s*\((\d{4})\)$', line)
                if match:
                    to_process.append((match.group(1).strip(), int(match.group(2))))
                    
        if not to_process:
            print("Plik 'seriale.txt' nie zawiera poprawnych wpisów. Upewnij się, że wpisano np. 'Lost, 2004'")
            return
            
        print(f"Odnaleziono {len(to_process)} pozycji do przetworzenia. Rozpoczynanie importu masowego...")
        success_count = 0
        for title, year in to_process:
            if add_single_show(html_file, title, year, is_bulk=True):
                success_count += 1
        print(f"\nUkończono import masowy! Pomyślnie dodano {success_count} z {len(to_process)} seriali.")
        
    else:
        while True:
            print("\n" + "="*50)
            title = input("Wprowadź tytuł serialu (lub naciśnij Enter, aby zakończyć): ").strip()
            if not title:
                print("Zamykanie programu.")
                break
            year = input("Wprowadź rok produkcji (np. 2022): ").strip()
            if not year.isdigit():
                print("[Błąd] Rok musi składać się wyłącznie z cyfr!")
                continue
            add_single_show(html_file, title, year, is_bulk=False)

if __name__ == "__main__":
    main()