"""Inspect supplied Michigan PDFs for subgroup sample-size documentation."""

from io import BytesIO
from urllib.request import urlopen

from pypdf import PdfReader


DOC_IDS = ("74465", "77767", "80186", "81744", "82119", "82118")
TERMS = (
    "sample size",
    "number of interviews",
    "weighted base",
    "n =",
    " n=",
)


def main() -> None:
    for doc_id in DOC_IDS:
        url = f"https://data.sca.isr.umich.edu/fetchdoc.php?docid={doc_id}"
        reader = PdfReader(BytesIO(urlopen(url, timeout=60).read()))
        pages = [page.extract_text() or "" for page in reader.pages]
        print(f"docid={doc_id} pages={len(pages)}")
        for term in TERMS:
            matches = [str(index + 1) for index, page in enumerate(pages) if term in page.lower()]
            print(f"  {term}: {', '.join(matches) if matches else 'none'}")


if __name__ == "__main__":
    main()
