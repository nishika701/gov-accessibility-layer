import re


STOP_WORDS = {
    "what",
    "is",
    "the",
    "a",
    "an",
    "of",
    "to",
    "for",
    "and",
    "in",
    "on",
    "are",
    "do",
    "i",
    "you",
    "can",
    "this",
    "that"
}


def tokenize(text):
    words = re.findall(r"\b[a-zA-Z0-9]+\b", text.lower())

    return {
        word
        for word in words
        if word not in STOP_WORDS
    }


def retrieve(query, sections, top_k=3):

    query_words = tokenize(query)

    scored = []

    for section in sections:

        section_words = tokenize(section)

        overlap = query_words.intersection(section_words)

        score = len(overlap)

        if score > 0:
            scored.append(
                (score, section)
            )

    scored.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return [
        section
        for _, section in scored[:top_k]
    ]


if __name__ == "__main__":

    sections = [
        "The applicant must provide identity proof.",
        "The applicant must provide proof of address.",
        "The application must be submitted before the deadline.",
    ]

    results = retrieve(
        "What identity documents are required?",
        sections
    )

    for result in results:
        print(result)