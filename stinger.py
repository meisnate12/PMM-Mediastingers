import os, re, requests, ruamel.yaml # noqa
from datetime import datetime
from tmdbapis import TMDbAPIs, TMDbException
from lxml import html

tmdb = TMDbAPIs(os.getenv("TMDBAPI"))
url = "http://www.mediastinger.com/movies-with-stingers/"
page_num = 0
data = {}

yaml = ruamel.yaml.YAML()
yaml.indent(mapping=2, sequence=2)
with open("tmdb_override.yml", encoding="utf-8") as fp:
    ov_data = yaml.load(fp)
    override = {t: i for t, i in ov_data.items()}

print_data = {}
while url:
    page_num += 1
    print_data[page_num] = {"url": url}
    response = html.fromstring(requests.get(url).content)
    next_page = response.xpath("//a[@title='Next page']/@href")
    url = next_page[0] if next_page else None
    rows = []
    for item in response.xpath("//ul[@class='highlights showhidehtml commonclssearch divwidth']/li"): # noqa
        title = item.xpath("a/span/div/text()")
        if title:
            title = title[0].strip()
            try:
                rating = int(item.xpath("span/div/text()")[0].strip())
            except ValueError:
                rating = 0
            rating_str = f"{'+' if rating > 0 else ''}{rating}"
            vgs = item.xpath("span/span/a/@href")
            if any(["video-games" in v for v in vgs]):
                rows.append(("", rating_str, title, "WARNING IGNORED: Item is a Video Game"))
                continue

            res = re.search(r"(.*) \((\d*)\)", title)
            search_title = res.group(1) if res else title
            search_year = int(res.group(2)) if res else None
            tmdb_id = None
            tmdb_title = None
            tmdb_item = None
            if title in override:
                tmdb_item = tmdb.movie(override[title])
            else:
                try:
                    searches = tmdb.movie_search(search_title, year=search_year)
                    tmdb_item = searches.results[0]
                except TMDbException:
                    try:
                        searches = tmdb.movie_search(search_title)
                        tmdb_item = searches.results[0]
                    except TMDbException:
                        rows.append(("", rating_str, title, "WARNING IGNORED: TMDb ID Not Found"))
                        continue
            tmdb_title = f"{tmdb_item.name} ({tmdb_item.release_date.year})"
            if tmdb_title == title:
                tmdb_title = ""
            rows.append((str(tmdb_item.id), rating_str, title, tmdb_title))
            data[tmdb_item.id] = rating
    print_data[page_num]["rows"] = rows

id_max = len("TMDb ID")
rating_max = len("Rating")
title_max = len("MediaStinger Title")
tmdb_max = len("Message or TMDb Title If different")
for i, p_data in print_data.items():
    _id_max = len(max(p_data["rows"], key=lambda t: len(t[0]))[0])
    if _id_max > id_max:
        id_max = _id_max
    _rating_max = len(max(p_data["rows"], key=lambda t: len(t[1]))[1])
    if _rating_max > rating_max:
        rating_max = _rating_max
    _title_max = len(max(p_data["rows"], key=lambda t: len(t[2]))[2])
    if _title_max > title_max:
        title_max = _title_max
    _tmdb_max = len(max(p_data["rows"], key=lambda t: len(t[3]))[3])
    if _tmdb_max > tmdb_max:
        tmdb_max = _tmdb_max

for i, p_data in print_data.items():
    if i > 1:
        print()
    print(f"| Page {i}: {p_data['url']}")
    print(f"| {'TMDb ID':^{id_max}} | {'Rating':^{rating_max}} | {'MediaStinger Title':<{title_max}} | {'Message or TMDb Title If different':<{tmdb_max}} |")
    print(f"|{'-' * (id_max + 2)}|{'-' * (rating_max + 2)}|{'-' * (title_max + 2)}|{'-' * (tmdb_max + 2)}|")
    for row in p_data["rows"]:
        print(f"| {row[0]:^{id_max}} | {row[1]:^{rating_max}} | {row[2]:<{title_max}} | {row[3]:<{tmdb_max}} |")

yaml = ruamel.yaml.YAML()
yaml.indent(mapping=2, sequence=2)
with open("stingers.yml", 'w', encoding="utf-8") as fp:
    yaml.dump(data, fp)


with open("README.md", "r") as f:
    readme_data = f.readlines()

readme_data[1] = f"Last generated at: {datetime.utcnow().strftime('%B %d, %Y %I:%M %p')} UTC\n"

with open("README.md", "w") as f:
    f.writelines(readme_data)
