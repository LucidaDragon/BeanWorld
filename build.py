import json, os, re, shutil, sys

CURRENT_DIRECTORY = __file__[:__file__.replace("\\", "/").rindex("/")]
os.chdir(CURRENT_DIRECTORY)

SITE_NAME = "BeanWiki"
DESCRIPTION_LENGTH = 200

SOURCE_DIRECTORY = "./src"

DICTIONARY_SOURCE = f"{SOURCE_DIRECTORY}/dictionary.json"
ORTHOGRAPHY_SOURCE = f"{SOURCE_DIRECTORY}/orthography.json"
EXAMPLES_SOURCE = f"{SOURCE_DIRECTORY}/examples.json"

OUTPUT_DIRECTORY = "./output"

DICTIONARY_DIRECTORY = f"{OUTPUT_DIRECTORY}/dictionary"
EXAMPLES_PAGE = f"{OUTPUT_DIRECTORY}/examples.html"

shutil.rmtree(OUTPUT_DIRECTORY)

with open(ORTHOGRAPHY_SOURCE, "r", encoding="utf-8") as stream:
	ORTHOGRAPHY = json.load(stream)

def ipa_to_orthography(ipa: str) -> str:
	result: list[str] = []
	for c in ipa:
		if ord(c) <= 64:
			result.append(c)
			continue
		
		if not c in ORTHOGRAPHY:
			print(f"Warning: {c} (in {ipa}) is not defined in the orthography.")
			return ipa
		
		result.append(ORTHOGRAPHY[c])
	
	return "".join(result)

def escape(text: str) -> str:
	return text.replace("&", "&amp;").replace("\"", "&quot;").replace("'", "&apos;").replace("<", "&lt;").replace(">", "&gt;")

def word_to_link(ipa: str, text: str, tooltip: str | None = None, relative_to: str = ".") -> str:
	def tooltip_attribute() -> str: return f"title=\"{escape(tooltip)}\" "
	return f"<a {tooltip_attribute() if tooltip != None else ''}href=\"{escape(relative_to)}{escape(DICTIONARY_DIRECTORY[len(OUTPUT_DIRECTORY):])}/{escape(ipa.strip())}.html\">{escape(text)}</a>"

def extract_words(ipas: str) -> list[str]:
	return re.findall(r"[^\0-\100\133-\140\173-\177]+", ipas)

def words_to_links(ipas: str, relative_to: str = ".") -> str:
	return re.sub(r"[^\0-\100\133-\140\173-\177]+", lambda match: word_to_link(match[0], ipa_to_orthography(match[0]), tooltip=match[0], relative_to=relative_to), ipas)

def get_html_header(page_title: str, group_title: str, description: str, type: str = "website", css: str = "style.css", **kwargs) -> str:
	metadata = { "og:type": type, "og:title": page_title, "og:site_name": group_title, "og:description": description }
	for key in kwargs: metadata[f"og:{key}"] = kwargs[key]
	return f'<head><title>{escape(page_title)} - {escape(group_title)}</title><link rel="stylesheet" href="{escape(css)}">' + "".join([f'<meta property="{escape(key)}" content="{escape(metadata[key])}">' for key in metadata]) + "</head>"

def markdown_to_html(md: str) -> str:
	DEFAULT_MODE = "default"
	TABLE_MODE = "table"
	
	mode = DEFAULT_MODE
	result: list[str] = []
	table_header_line: str = ""
	
	def is_tag() -> bool: return len(result) == 0 or result[-1].endswith(">")
	def append_text(text: str) -> None: result.append(f"{'<p>' if is_tag() else '<br>'}{escape(text)}")
	
	for line in md.split("\n"):
		if mode == TABLE_MODE:
			if table_header_line != "" and len(line.split("|")) != len(table_header_line.split("|")):
				append_text(table_header_line)
				mode = DEFAULT_MODE
			elif table_header_line != "":
				result.append("<table><thead>" + "".join([f"<th>{escape(column.strip())}</th>" for column in table_header_line.split("|")]) + "</thead><tbody>")
				table_header_line = ""
			elif line == "":
				result.append("</tbody></table>")
				mode = DEFAULT_MODE
				continue
			else:
				result.append("<tr>" + "".join([f"<td>{escape(column.strip())}</td>" for column in line.split("|")]) + "</tr>")
		
		if mode == DEFAULT_MODE:
			if line.startswith("#"):
				if not is_tag(): result.append("</p>")
				
				stripped = line.lstrip("#")
				depth = len(line) - len(stripped)
				result.append(f"<h{depth}>{escape(stripped.strip())}</h{depth}>")
			elif line == "":
				if not is_tag(): result.append("</p>")
			elif "|" in line:
				table_header_line = line
				mode = TABLE_MODE
			elif "`" in line:
				line = escape(line)
				result.append("<p>" if is_tag() else "<br>")
				result.append(re.sub(r"`([^`]*)`", lambda match: escape("\"") + words_to_links(match[1]) + escape("\""), line))
				if is_tag(): result.append("")
			else:
				append_text(line)
	
	if not is_tag(): result.append("</p>")
	
	return "".join(result)

def extract_html_description(html: str) -> str:
	result = ""
	for match in re.findall(r"<p>([^<>]+)</p>", html):
		result = f"{result} {match}"
		if len(result) >= DESCRIPTION_LENGTH: break
	return result.strip()

def build_markdown() -> None:
	os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)
	for _, _, files in os.walk(SOURCE_DIRECTORY):
		for file in files:
			if file.endswith(".md"):
				with open(f"{SOURCE_DIRECTORY}/{file}", "r", encoding="utf-8") as stream:
					html = markdown_to_html(stream.read())
				
				name = ".".join(file.split(".")[:-1])
				with open(f"{OUTPUT_DIRECTORY}/{name}.html", "w", encoding="utf-8") as stream:
					stream.write("<!DOCTYPE html><html>")
					stream.write(get_html_header(name.replace("_", " ").capitalize(), SITE_NAME, extract_html_description(html)))
					stream.write("<body>")
					stream.write(html)
					stream.write("</body></html>")
		break

def build_dictionary(examples: dict[str, list[dict[str, str]]]) -> None:
	os.makedirs(DICTIONARY_DIRECTORY, exist_ok=True)
	
	with open(DICTIONARY_SOURCE, "r", encoding="utf-8") as stream:
		words: dict[str, list[dict[str, str | list]]] = json.load(stream)
	
	for ipa in words:
		with open(f"{DICTIONARY_DIRECTORY}/{ipa}.html", "w", encoding="utf-8") as stream:
			stream.write("<!DOCTYPE html><html>")
			stream.write(get_html_header(ipa_to_orthography(ipa), SITE_NAME, f"/{ipa}/ Definition & Examples", css="../style.css"))
			stream.write(f"<body><h1>{escape(ipa_to_orthography(ipa))}</h1><p>/{escape(ipa)}/</p>")
			
			for entry in words[ipa]:
				stream.write(f"<h2>{escape(entry['type'])}</h2><p>{escape(entry['definition'])}</p>\n\n")
				
			if ipa in examples:
				stream.write("<h2>Examples</h2><table>")
				
				for example in examples[ipa]:
					stream.write(f"<tr><td>{escape(example['english'])}</td><td>{words_to_links(example['ipa'], relative_to='..')}</td>")
				
				stream.write("</table>")
			
			stream.write("</body></html>")
	
	with open(f"{DICTIONARY_DIRECTORY}/index.html", "w", encoding="utf-8") as stream:
		stream.write("<!DOCTYPE html><html>")
		stream.write(get_html_header("Dictionary", SITE_NAME, "Browse the dictionary.", css="../style.css"))
		stream.write("<body><h1>Dictionary</h1><p>See the <a href=\"../examples.html\">examples</a> for a list of examples.</p>")
		
		for ipa in words:
			stream.write(words_to_links(ipa, ".."))
			stream.write("<br>")
		
		stream.write("</body></html>")

def build_examples() -> dict[str, list[dict[str, str]]]:
	os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)
	
	with open(EXAMPLES_SOURCE, "r", encoding="utf-8") as stream:
		examples: list[dict[str, str]] = json.load(stream)
	
	result: dict[str, list[dict[str, str]]] = {}
	with open(EXAMPLES_PAGE, "w", encoding="utf-8") as stream:
		stream.write("<!DOCTYPE html><html>")
		stream.write(get_html_header("Example Statements", SITE_NAME, "Example translations to english and IPA."))
		stream.write(f"<body><h1>Examples</h1><p>See the <a href=\"./dictionary/index.html\">dictionary</a> for a list of all words.</p><table>")
		for example in examples:
			for word in extract_words(example["ipa"]):
				if word in result: result[word].append(example)
				else: result[word] = [example]
			stream.write(f"<tr><td>{escape(example['english'])}</td><td>{words_to_links(example['ipa'])}</td></tr>")
		stream.write("</table></body></html>")
	
	return result

def build_files(filter: list[str]) -> None:
	os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)
	
	for _, _, files in os.walk(SOURCE_DIRECTORY):
		for file in files:
			if any([file.endswith(f".{suffix}") for suffix in filter]):
				shutil.copyfile(f"{SOURCE_DIRECTORY}/{file}", f"{OUTPUT_DIRECTORY}/{file}")
		break

build_markdown()
build_dictionary(build_examples())
build_files(["html", "css", "js", "png"])