import fitz

def extract_pdf_content(pdf_path: str, doc_prefix: str = "doc") -> dict:
    doc = fitz.open(pdf_path)
    full_text = ""
    images = []
    seen_xrefs = {}

    for page_num, page in enumerate(doc, start=1):
        full_text += f"\n--- Page {page_num} ---\n"
        full_text += page.get_text()

        for img_index, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            ref = f"{doc_prefix}_image_page_{page_num}_index_{img_index}"

            if xref in seen_xrefs:
                images.append({
                    "page": page_num,
                    "index": img_index,
                    "data": seen_xrefs[xref]["data"],
                    "ext": seen_xrefs[xref]["ext"],
                    "ref": ref,
                })
                continue

            try:
                img_data = doc.extract_image(xref)
                if len(img_data["image"]) < 5120:
                    continue
                seen_xrefs[xref] = {"data": img_data["image"], "ext": img_data["ext"]}
                images.append({
                    "page": page_num,
                    "index": img_index,
                    "data": img_data["image"],
                    "ext": img_data["ext"],
                    "ref": ref,
                })
            except Exception as e:
                print(f"  Warning: Could not extract image on page {page_num} index {img_index}: {e}")

    return {
        "text": full_text.strip(),
        "images": images,
        "pages": len(doc)
    }
