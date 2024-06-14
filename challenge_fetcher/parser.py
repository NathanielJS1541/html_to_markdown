import bs4
import challenge_fetcher
import challenge_fetcher.scraper
import re


"""
CHALLENGE_URL_REGEX is a compiled regular expression that matches strings of the form "problem=<number>":
  - "^" asserts the start of a line.
  - "problem=" matches the literal string "problem=".
  - "(?P<number>\d+)" is a named capturing group to capture one or more digits:
    - "(...)" defines the capture group.
    - "?P<number>" names the capture group "number".
    - "\d" is a shorthand character class to capture digits (0-9).
    - "+" is a greedy quantifier that matches one or more times, and allows the previous character class to capture one or more digits.
"""
CHALLENGE_URL_REGEX = re.compile(r"^problem=(?P<number>\d+)")

"""
RESOURCE_URL_REGEX is a compiled regular expression that matches strings of the form "resources/<optional_path>/<filename>",
"project/resources/<optional_path>/<filename>", "images/<optional_path>/<filename>", and "project/images/<optional_path>/<filename>":
  - "^" asserts the start of a line.
  - "(project\/)?" is a capture group that matches the optional literal string "project/".
    - "(...)" defines the capture group.
    - "?" makes the capture group optional.
  - "(resources|images)" matches either the literal string "resources" or "images".
    - "(...)" defines the capture group.
    - "resources" matches the literal string "resources".
    - "|" is the OR operator.
    - "images" matches the literal string "images".
  - "\/" matches the literal string "/".
  - "(.+\/)?" is an optional capture group to match any characters followed by a "/":
    - "(...)" defines the capture group.
    - "." matches any character (except for a newline).
    - "+" is a greedy quantifier that matches one or more times, and allows the previous character class to capture one or more word characters.
    - "\/" matches the literal "/".
    - "?" makes the capture group optional.
  - "(?P<filename>.+)" is a named capturing group to match any characters:
    - "(...)" defines the capture group.
    - "?P<filename>" names the capture group "filename".
    - "." matches any character (except for a newline).
    - "+" is a greedy quantifier that matches one or more times, and allows the previous character class to capture one or more word characters.
"""
RESOURCE_URL_REGEX = re.compile(
    r"^(project\/)?(resources|images)\/(.+\/)?(?P<filename>.+)"
)

"""
ABOUT_URL_REGEX is a compiled regular expression that matches strings of the form "about=<word>":
  - "^" asserts the start of a line.
  - "about=" matches the literal string "about=".
  - "(\w+)" is a capturing group to capture one or more word characters:
    - "(...)" defines the capture group.
    - "\w" is a shorthand character class to capture word characters (a-z, A-Z, 0-9, _).
    - "+" is a greedy quantifier that matches one or more times, and allows the previous character class to capture one or more word characters.
"""
ABOUT_URL_REGEX = re.compile(r"^about=(\w+)")


def convert_urls_to_markdown(content: bs4.Tag) -> dict[str, str] | None:
    """convert_urls_to_markdown Convert all URLs in the bs4.Tag to MarkDown links.

    This replaces any <a href=""> tags with the equivelant MarkDown syntax, and additionally corrects those URLs
    based on the type of URL:
      - Links to other challenges are corrected to the full URL to the challenge page on the Project Euler website.
      - Links to remote content are corrected to a link to a file locally, and the file URL is recorded for download.
      - Links to the Project Euler about pages (https://projecteuler.net/about) are updated to full URLs.

    Args:
        content (bs4.Tag): The bs4.Tag containing the challenge descrioption.

    Raises:
        KeyError: Multiple resource files with the same name were found on the page.
        NotImplementedError: An undefined resource type was found on the page.

    Returns:
        dict[str, str] | None: A dictionary containing resource URLs keyed by file name to download, or None if no remote content is needed.
    """

    # Create an empty dictionary to store remote content filenames and URLs.
    remote_content = {}

    # Loop through all "a" tags in the content.
    for link in content.find_all("a"):
        # Get the URL from the tag.
        url = link.get("href")

        # Run compiled Regex expressions against the url to determine the type of content.
        challenge_match = CHALLENGE_URL_REGEX.search(url)  # Links to another challenge.
        resource_match = RESOURCE_URL_REGEX.search(
            url
        )  # Links to resources such as images and files.
        about_match = ABOUT_URL_REGEX.search(
            url
        )  # Links to the Project Euler "about" pages (https://projecteuler.net/about).

        if challenge_match:
            # This type of link is a reference to another challenge.

            # TODO: If problem is going to be downloaded, link it locally.

            # Get the linked challenge number from the named capture group.
            challenge_number = challenge_match.group("number")

            # Construct a URL to the remote challenge page.
            url = f"{challenge_fetcher.scraper.CHALLENGE_URL_BASE}{challenge_number}"
        elif resource_match:
            # This type of link is a reference to a resource such as an image or file. We will download these
            # locally so they can committed to the repo and linked locally in the README.

            # Get the linked file name from the Regex expression's named capture group.
            file_name = sanitise_file_name(resource_match.group("filename"))

            # Construct a URL for the remote content based on the base URL, and the complete URL that the Regex
            # matched.
            remote_url = challenge_fetcher.scraper.URL_BASE + url

            # Swap the "URL" to a local reference to the file_name, so the README will link to the local file once it
            # has been downloaded.
            url = f"./{file_name}"

            # For now, I'm assuming that each page will contain all uniquely named files. This will raise an error
            # if this assumption is incorrect, so I can fix it later :).
            if file_name in remote_content:
                raise KeyError(f"Multiple resources found with the name {file_name}")

            # Add the remote URL to the remote_content dictionary, keyed by the file_name that the resource needs to be
            # downloaded to.
            remote_content[file_name] = remote_url
        elif about_match:
            # This type of link is a reference to the "about" pages on different topics on the Project Euler website.
            # This content won't be downloaded, and a link to the about page will just be added to the README.

            # The URL from the bs4.Tag will be a relative URL. All we need to do to get a valid URL is add it to the
            # Project Euler base URL.
            url = f"{challenge_fetcher.scraper.URL_BASE}{url}"
        else:
            # Since I don't have the time (or willpower) to download and check every single challenge on the Project
            # Euler website, this error will alert me (or anyone else) to a link type that I haven't come accross yet.
            # If this is raised, inspect the URL and add some more Regex and handling (or open an issue on
            # https://github.com/NathanielJS1541/100_languages_template) :).
            raise NotImplementedError(
                f"A URL was found to an unknown resource type: {url}"
            )

        # Replace the link ("<a>") tag with the MarkDown representation of the new URL.
        link.replace_with(f"[{link.string}]({url})")

    if not remote_content:
        # If no remote content was found, return None.
        return None
    else:
        # If there is remote content, return the dictionary storing it.
        return remote_content


def sanitise_tag_text(description: bs4.Tag, github_workaround: bool) -> str:
    """sanitise_tag_text Sanitise the content of a bs4.Tag, and return it as a string.

    The text content of a bs4.Tag is "sanitised" to ensure that it is compatable with MarkDown. This includes an
    optional workaround for the GitHub MarkDown renderer. The sanitised content is then returned as a string.

    Args:
        description (bs4.Tag): The bs4.Tag containing the challenge description.
        github_workaround (bool): If True, a workaround for the GitHub MarkDown renderer not rendering the LaTeX /opcode function will be applied.

    Returns:
        str: A string that is MarkDown-compatible, which contains the description for the Project Euler challenge.
    """

    # Get the text contained in the BeautifulSoup tag.
    description_text = description.text

    # For markdown, a newline is not only represented by a /n, but two spaces followed by a /n. This is to get the same visual effect as a
    # new paragraph in the HTML.
    description_text = description_text.replace("\n", "  \n")

    # Workaround for GitHub not supporting \operatorname anymore (see https://github.com/github/markup/issues/1688).
    if github_workaround and "\\operatorname" in description_text:
        # RegEx pattern to replace the occurrances of \operatorname in the description:
        # - "\\operatorname\{" matches the literal string \operatorname{ (with escape character for the \ and {).
        # - "(.+?)" creates a capture group which matches the following:
        #   - "." matches any character.
        #   - "+" quantifier meaning that the previous "." can match one or more times.
        #   - "?" makes the "+" quantifier lazy. It will try and match as few characters as possible while still
        #     matching the next "}".
        # - "\}" matches the literal string }.
        # - "(.+?)" creates another capture group, as above.
        # - "=" matches the literal string = at the end of the expression.
        pattern = r"\\operatorname\{(.+?)\}(.+?)="

        # Replacement expression to define how the capture groups are included in the replaced text:
        # - "\\mathop{\\text{" is the literal string that will replace \operatorname{ with \mathop{\text{.
        # - "\1" is a backreference to the first capture group in the pattern. This corresponds to text captured by
        #   "(.+?)" inside the \\operatorname{...} in the original string.
        # - "}}" is the literal string which will close the \text{} and \mathop{} LaTeX commands.
        # - "\2" is a backreference to the second capture group in the pattern. This corresponds to the text captured
        #   by "(.+?)" between the "}" and "=" in the original string.
        # - "=" is the literal string =, which ends the replacement.
        replacement = r"\\mathop{\\text{\1}}\2="

        # Use the RegEx pattern and replacement strings to replace \operatorname{...} with \mathop{\text{...}} in the
        # description text.
        description_text = re.sub(pattern, replacement, description_text)

    return description_text
