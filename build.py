import json, os, re, shutil, xml.dom.minidom
from typing import cast

os.chdir(__file__[:__file__.replace("\\", "/").rindex("/")])

# SITE_NAME = "BeanWiki"
# DESCRIPTION_LENGTH = 200

# SOURCE_DIRECTORY = "./src"

# PHONETICS_SOURCE = f"{SOURCE_DIRECTORY}/phonetics-template.xml"
# DICTIONARY_SOURCE = f"{SOURCE_DIRECTORY}/dictionary.json"
# ORTHOGRAPHY_SOURCE = f"{SOURCE_DIRECTORY}/orthography.json"
# LATINIZATION_SOURCE = f"{SOURCE_DIRECTORY}/latinization.json"
# EXAMPLES_SOURCE = f"{SOURCE_DIRECTORY}/examples.json"
# ENGLISH_SOURCE = f"{SOURCE_DIRECTORY}/simplified-english.txt"

# OUTPUT_DIRECTORY = "./output"

# INCLUDE = ["style.css", "editor.html", "orthography.json", "dictionary.json"]
# PHONETICS_PAGE = f"{OUTPUT_DIRECTORY}/phonetics.html"
# DICTIONARY_DIRECTORY = f"{OUTPUT_DIRECTORY}/dictionary"
# EXAMPLES_PAGE = f"{OUTPUT_DIRECTORY}/examples.html"

# WORD_REGEX = re.compile(r"[^\0-\46\50-\100\133-\140\173-\177]+")

class Meaning:
	def __init__(self, definition: str | None = None, type: str | None = None, translations: list[str] | None = None, **kwargs) -> None:
		self.definition = definition
		self.type = type
		self.translations = translations

class Example:
	def __init__(self, english: str | None = None, ipa: str | None = None, **kwargs) -> None:
		self.english = english
		self.ipa = ipa

class Coverage:
	def __init__(self, build: "Build") -> None:
		self.build = build
	
	def print(self) -> None:
		build: "Build" = self.build
		missing_translations: set[str] = set()
		english_coverage: set[str] = set()
		variations: int = 0
		
		for ipa in build.dictionary:
			for entry in build.dictionary[ipa]:
				if entry.translations is None:
					missing_translations.add(ipa)
					continue
				
				for english in entry.translations: english_coverage.add(english.lower())
				variations += 1
		
		remaining_english: list[str] = []
		with open(build.english_source(), "r") as stream:
			for line in stream.readlines():
				english_word = line.strip().lower()
				if english_word.startswith("#"): continue
				
				if english_word != "" and not (english_word in english_coverage):
					remaining_english.append(english_word)
		
		finished_examples: list[Example] = []
		fully_covered_examples: list[Example] = []
		for example in build.examples:
			if example.english is None: continue
			
			covered: bool = True
			for english_word in re.split(r"[^\w]+", example.english):
				if english_word in english_coverage: continue
				covered = False
			
			if covered:
				fully_covered_examples.append(example)
			
			if example.ipa is None or example.ipa.strip() == "": continue
			finished_examples.append(example)
		
		english_coverage_percentage = int((len(english_coverage) * 10000) / (len(remaining_english) + len(english_coverage))) / 100
		print(f"English Coverage: {len(english_coverage)} english words ({english_coverage_percentage}%) with {len(build.dictionary)} bean words ({variations} variations).")
		
		if len(remaining_english) > 0:
			top_words: list[str] = []
			for i in range(min(len(remaining_english), 10)): top_words.append(remaining_english[i])
			print(f"Top 10 Missing English Words: {', '.join(top_words)}")
		
		print(f"Example Coverage: {len(finished_examples)}/{len(build.examples)} complete, with {len(fully_covered_examples)} more that are incomplete but fully covered.")
		
		if len(missing_translations) > 0:
			print(f"Missing Translations: {', '.join(missing_translations)}")

class Build:
	def __init__(self, site_name: str, include: list[str], source_directory: str = "./src", output_directory: str = "./output", word_regex: re.Pattern = re.compile(r"[^\0-\46\50-\100\133-\140\173-\177]+"), description_length: int = 200) -> None:
		self.site_name = site_name
		self.description_length = description_length
		self.source_directory = source_directory
		self.output_directory = output_directory
		self.include = include
		self.word_regex = word_regex
		
		with open(self.dictionary_source(), "r", encoding="utf-8") as stream:
			self.dictionary: dict[str, list[Meaning]] = {}
			raw_dictionary: dict[str, list[dict]] = json.load(stream)
			for word in raw_dictionary: self.dictionary[word] = [Meaning(**meaning) for meaning in raw_dictionary[word]]
		
		with open(self.orthography_source(), "r", encoding="utf-8") as stream:
			self.orthography: dict[str, str] = json.load(stream)
		
		with open(self.latinization_source(), "r", encoding="utf-8") as stream:
			self.latinization: dict[str, str] = json.load(stream)
		
		with open(self.examples_source(), "r", encoding="utf-8") as stream:
			self.examples: list[Example] = []
			for example in json.load(stream): self.examples.append(Example(**example))
	
	def build(self) -> None:
		shutil.rmtree(self.output_directory)
		self.build_phonetics()
		self.build_markdown()
		self.build_examples()
		self.build_dictionary()
		self.build_files()
	
	def coverage(self) -> Coverage:
		return Coverage(self)
	
	def phonetics_source(self) -> str:
		return f"{self.source_directory}/phonetics-template.xml"
	
	def phonetics_page(self) -> str:
		return f"{self.output_directory}/phonetics.html"
	
	def dictionary_source(self) -> str:
		return f"{self.source_directory}/dictionary.json"
	
	def dictionary_directory(self) -> str:
		return f"{self.output_directory}/dictionary"
	
	def orthography_source(self) -> str:
		return f"{self.source_directory}/orthography.json"
	
	def latinization_source(self) -> str:
		return f"{self.source_directory}/latinization.json"
	
	def examples_source(self) -> str:
		return f"{self.source_directory}/examples.json"
	
	def examples_page(self) -> str:
		return f"{self.output_directory}/examples.html"
	
	def english_source(self) -> str:
		return f"{self.source_directory}/simplified-english.txt"
	
	@staticmethod
	def ipa_to_orthography(ipa: str, orthography: dict[str, str], join_with: str = "") -> str:
		if ipa.startswith("'") and ipa.endswith("'"): return ipa[1:-1]
		
		result: list[str] = []
		for c in ipa:
			if ord(c) <= 64:
				result.append(c)
				continue
			
			if not c in orthography:
				print(f"Warning: {c} (in {ipa}) is not defined in the orthography.")
				return ipa
			
			result.append(orthography[c])
		
		return join_with.join(result)
	
	@staticmethod
	def escape(text: str) -> str:
		return text.replace("&", "&amp;").replace("\"", "&quot;").replace("'", "&apos;").replace("<", "&lt;").replace(">", "&gt;")
	
	def word_to_link(self, ipa: str, text: str, tooltip: str | None = None, relative_to: str = ".") -> str:
		if ipa.startswith("'") and ipa.endswith("'"): return f"<i>{Build.escape(text)}</i>"
		def tooltip_attribute() -> str: return f"title=\"{Build.escape(cast(str, tooltip))}\" "
		if ipa in self.dictionary: return f"<a {tooltip_attribute() if tooltip != None else ''}href=\"{Build.escape(relative_to)}{Build.escape(self.dictionary_directory()[len(self.output_directory):])}/{Build.escape(ipa.strip())}.html\">{Build.escape(text)}</a>"
		else: return f"<u {tooltip_attribute() if tooltip != None else ''}>{Build.escape(text)}</u>"
	
	def extract_words(self, ipas: str) -> list[str]:
		return self.word_regex.findall(ipas)
	
	def words_to_links(self, ipas: str, relative_to: str = ".") -> str:
		return self.word_regex.sub(lambda match: self.word_to_link(match[0], Build.ipa_to_orthography(match[0], self.orthography), tooltip=match[0], relative_to=relative_to), ipas)
	
	def get_examples_for_word(self, ipa: str) -> list[Example]:
		result: list[Example] = []
		for example in self.examples:
			if (example.ipa is None) or (example.ipa == ""): continue
			elif ipa in self.extract_words(example.ipa):
				result.append(example)
		return result
	
	@staticmethod
	def get_html_header(page_title: str, group_title: str, description: str, type: str = "website", css: str = "style.css", **kwargs) -> str:
		metadata = { "og:type": type, "og:title": page_title, "og:site_name": group_title, "og:description": description }
		for key in kwargs: metadata[f"og:{key}"] = kwargs[key]
		return f'<head><meta charset="UTF-8"><title>{Build.escape(page_title)} - {Build.escape(group_title)}</title><link rel="stylesheet" href="{Build.escape(css)}"><meta name="viewport" content="width=device-width, initial-scale=1.0">' + "".join([f'<meta property="{Build.escape(key)}" content="{Build.escape(metadata[key])}">' for key in metadata]) + "</head>"
	
	def markdown_to_html(self, md: str) -> str:
		DEFAULT_MODE = "default"
		TABLE_MODE = "table"
		
		mode = DEFAULT_MODE
		result: list[str] = []
		table_header_line: str = ""
		
		def is_tag() -> bool: return len(result) == 0 or result[-1].endswith(">")
		def append_text(text: str) -> None: result.append(f"{'<p>' if is_tag() else '<br>'}{Build.escape(text)}")
		
		for line in md.split("\n"):
			if mode == TABLE_MODE:
				if table_header_line != "" and len(line.split("|")) != len(table_header_line.split("|")):
					append_text(table_header_line)
					mode = DEFAULT_MODE
				elif table_header_line != "":
					result.append("<table><thead>" + "".join([f"<th>{Build.escape(column.strip())}</th>" for column in table_header_line.split("|")]) + "</thead><tbody>")
					table_header_line = ""
				elif line == "":
					result.append("</tbody></table>")
					mode = DEFAULT_MODE
					continue
				else:
					result.append("<tr>" + "".join([f"<td>{Build.escape(column.strip())}</td>" for column in line.split("|")]) + "</tr>")
			
			if mode == DEFAULT_MODE:
				if line.startswith("#"):
					if not is_tag(): result.append("</p>")
					
					stripped = line.lstrip("#")
					depth = len(line) - len(stripped)
					result.append(f"<h{depth}>{Build.escape(stripped.strip())}</h{depth}>")
				elif line == "":
					if not is_tag(): result.append("</p>")
				elif "|" in line:
					table_header_line = line
					mode = TABLE_MODE
				elif "`" in line:
					line = Build.escape(line)
					result.append("<p>" if is_tag() else "<br>")
					result.append(re.sub(r"`([^`]*)`", lambda match: Build.escape("\"") + self.words_to_links(match[1]) + Build.escape("\""), line))
					if is_tag(): result.append("")
				else:
					append_text(line)
		
		if not is_tag(): result.append("</p>")
		
		return "".join(result)
	
	def extract_html_description(self, html: str) -> str:
		result = ""
		for match in re.findall(r"<p>([^<>]+)</p>", html):
			result = f"{result} {match}"
			if len(result) >= self.description_length: break
		return result.strip()
	
	def build_markdown(self) -> None:
		os.makedirs(self.output_directory, exist_ok=True)
		for _, _, files in os.walk(self.source_directory):
			for file in files:
				if file.endswith(".md"):
					with open(f"{self.source_directory}/{file}", "r", encoding="utf-8") as stream:
						html = self.markdown_to_html(stream.read())
					
					name = ".".join(file.split(".")[:-1])
					with open(f"{self.output_directory}/{name}.html", "w", encoding="utf-8") as stream:
						stream.write("<!DOCTYPE html><html>")
						stream.write(Build.get_html_header(name.replace("_", " ").capitalize(), self.site_name, self.extract_html_description(html)))
						stream.write("<body>")
						stream.write(html)
						stream.write("</body></html>")
			break
	
	def build_phonetics(self) -> None:
		os.makedirs(self.output_directory, exist_ok=True)
		shutil.copyfile(self.phonetics_source(), self.phonetics_page())
		
		dom: xml.dom.minidom.Document = xml.dom.minidom.parse(self.phonetics_source())
		node: xml.dom.minidom.Element
		
		for child in dom.getElementsByTagName("th"):
			node = child
			if len(node.childNodes) == 0:
				text = xml.dom.minidom.Text()
				text.nodeValue = ""
				node.appendChild(text)
		
		for child in dom.getElementsByTagName("td"):
			node = child
			if len(node.childNodes) == 0:
				text = xml.dom.minidom.Text()
				text.nodeValue = ""
				node.appendChild(text)
			else:
				for child in node.childNodes:
					if isinstance(child, xml.dom.minidom.Text):
						if not child.wholeText in self.orthography:
							child.nodeValue = ""
						else:
							child.nodeValue = f"/{child.wholeText}/ {self.orthography[child.wholeText]}"
		
		with open(self.phonetics_page(), "wb") as stream:
			root: xml.dom.minidom.Element = dom.getElementsByTagName("body")[0]
			stream.write("<!DOCTYPE html>\n<html>\n".encode("utf-8"))
			stream.write(Build.get_html_header("Phonetics", self.site_name, "Phonetic inventory and orthography.").encode("utf-8"))
			stream.write(root.toxml(encoding="utf-8"))
			stream.write("\n</html>".encode("utf-8"))
	
	def build_dictionary(self) -> None:
		os.makedirs(self.dictionary_directory(), exist_ok=True)
		
		english_coverage: set[str] = set()
		bean_variations: int = 0
		
		for ipa in self.dictionary:
			for entry in self.dictionary[ipa]:
				if entry.translations is None:
					print(f"Warning: {ipa} is missing translations.")
					continue
				
				for english in entry.translations: english_coverage.add(english.lower())
				bean_variations += 1
			
			with open(f"{self.dictionary_directory()}/{ipa}.html", "w", encoding="utf-8") as stream:
				stream.write("<!DOCTYPE html><html>")
				stream.write(self.get_html_header(Build.ipa_to_orthography(ipa, self.orthography), self.site_name, f"/{ipa}/ Definition & Examples", css="../style.css"))
				stream.write(f'<body><h1>{Build.escape(Build.ipa_to_orthography(ipa, self.orthography))}</h1><p>/{Build.escape(ipa)}/ "{Build.escape(self.ipa_to_orthography(ipa, self.latinization))}"</p>')
				
				for entry in self.dictionary[ipa]:
					if not isinstance(entry.type, str): raise ValueError(f"Expected string in type field but got {str(entry.type)}.")
					stream.write(f"<h2>{Build.escape(entry.type)}</h2><p>{Build.escape('' if entry.definition is None else entry.definition)}</p>\n\n")
				
				examples = self.get_examples_for_word(ipa)
				if len(examples) > 0:
					stream.write("<h2>Examples</h2><table>")
					
					for example in examples:
						if example.english is None: continue
						elif example.ipa is None or example.ipa == "": continue
						
						stream.write(f"<tr><td>{Build.escape(example.english)}</td><td>{self.words_to_links(example.ipa, relative_to='..')}</td>")
					
					stream.write("</table>")
				
				stream.write("</body></html>")
		
		with open(f"{self.dictionary_directory()}/index.html", "w", encoding="utf-8") as stream:
			stream.write("<!DOCTYPE html><html>")
			stream.write(Build.get_html_header("Dictionary", self.site_name, "Browse the dictionary.", css="../style.css"))
			stream.write("<body><h1>Dictionary</h1><p>See the <a href=\"../examples.html\">examples</a> for a list of examples.</p>")
			
			for ipa in self.dictionary:
				stream.write(self.words_to_links(ipa, ".."))
				stream.write("<br>")
			
			stream.write("</body></html>")
	
	def build_examples(self) -> None:
		os.makedirs(self.output_directory, exist_ok=True)
		
		with open(self.examples_page(), "w", encoding="utf-8") as stream:
			stream.write("<!DOCTYPE html><html>")
			stream.write(Build.get_html_header("Example Statements", self.site_name, "Example translations to english and IPA."))
			stream.write(f"<body><h1>Examples</h1><p>See the <a href=\"./dictionary/index.html\">dictionary</a> for a list of all words.</p><table>")
			
			for example in self.examples:
				if example.english is None: continue
				elif (example.ipa == "") or (example.ipa is None): continue
				stream.write(f"<tr><td>{Build.escape(example.english)}</td><td>{self.words_to_links(example.ipa)}</td></tr>")
			
			stream.write("</table></body></html>")
	
	def build_files(self) -> None:
		os.makedirs(self.output_directory, exist_ok=True)
		
		for file in self.include: shutil.copyfile(f"{self.source_directory}/{file}", f"{self.output_directory}/{file}")

build = Build("BeanWiki", ["style.css", "editor.html", "orthography.json", "dictionary.json"])
build.coverage().print()
build.build()