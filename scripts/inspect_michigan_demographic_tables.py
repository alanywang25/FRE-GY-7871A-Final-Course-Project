"""Print text from selected Michigan demographic-table PDFs for provenance checks."""

from io import BytesIO
from urllib.request import urlopen

from pypdf import PdfReader


URLS = (
    "https://data.sca.isr.umich.edu/get-demographic-table.php?g=age&d=a1834&y=2026&m=8&n=alln&p=m&f=pdf&k=8581604d0a9c6f8f922791911fb232e4c29305fac80381a7a1c068f4e2d02040",
    "https://data.sca.isr.umich.edu/get-demographic-table.php?g=age&d=a3554&y=2026&m=8&n=alln&p=m&f=pdf&k=5e82363f28ee6125d33acef1dd9d82bed514fa0f537d33df60cbb8c8ebdc06f9",
    "https://data.sca.isr.umich.edu/get-demographic-table.php?g=age&d=a5597&y=2026&m=8&n=alln&p=m&f=pdf&k=0e42df59c1dab09b0d99008912c8b7071bd17f7c3253738e8ab67d39ac89b51e",
)


def main() -> None:
    for url in URLS:
        document = urlopen(url, timeout=60).read()
        reader = PdfReader(BytesIO(document))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        print(f"PDF bytes={len(document)}, pages={len(reader.pages)}")
        print(text[:6_000])
        print("--- END PDF ---")


if __name__ == "__main__":
    main()
