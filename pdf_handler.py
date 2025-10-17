import os
from pathlib import Path
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
import fitz  # PyMuPDF

def merge_pdfs_by_subdirectory():
    """
    Look for 'pdfs' directory in current working directory.
    For each subdirectory in 'pdfs', merge all *.pdf files in that subdirectory
    and save the merged file in the 'pdfs' directory with the subdirectory name.

    Returns:
    list: List of successfully created merged PDF files
    """
    try:
        # Look for 'pdfs' directory in current working directory
        pdfs_dir = Path.cwd() / "pdfs"

        # Check if pdfs directory exists
        if not pdfs_dir.exists() or not pdfs_dir.is_dir():
            print(f"Error: 'pdfs' directory not found in current working directory")
            return []

        print(f"Processing subdirectories in: {pdfs_dir}")

        # Get all subdirectories in pdfs
        subdirectories = [d for d in pdfs_dir.iterdir() if d.is_dir()]

        if not subdirectories:
            print("No subdirectories found in 'pdfs' directory")
            return []

        successful_merges = []

        # Process each subdirectory
        for subdir in subdirectories:
            print(f"\nProcessing subdirectory: {subdir.name}")

            # Get PDF files in this subdirectory
            pdf_files = list(subdir.glob("*.pdf"))
            pdf_files = [f for f in pdf_files if f.is_file()]
            pdf_files.sort()  # Sort for consistent ordering

            if not pdf_files:
                print(f"  No PDF files found in '{subdir.name}'")
                continue

            print(f"  Found {len(pdf_files)} PDF files:")
            for pdf_file in pdf_files:
                print(f"    - {pdf_file.name}")

            # Create merger for this subdirectory
            merger = PdfMerger()
            merged_count = 0

            # Add each PDF to the merger
            for pdf_file in pdf_files:
                try:
                    print(f"    Adding {pdf_file.name}...")
                    merger.append(str(pdf_file))
                    merged_count += 1
                except Exception as e:
                    print(f"    Warning: Could not add {pdf_file.name}: {e}")
                    continue

            if merged_count == 0:
                print(f"  No files could be merged from '{subdir.name}'")
                merger.close()
                continue

            # Define output path in pdfs directory with subdirectory name
            output_filename = f"{subdir.name}.pdf"
            output_path = pdfs_dir / output_filename

            # Write merged PDF to output file
            try:
                with open(output_path, 'wb') as output_file:
                    merger.write(output_file)

                merger.close()

                print(f"  Successfully merged {merged_count} PDFs into '{output_path}'")
                successful_merges.append(str(output_path))

            except Exception as e:
                print(f"  Error writing merged file for '{subdir.name}': {e}")
                merger.close()
                continue

        print(f"\nCompleted processing. Successfully created {len(successful_merges)} merged PDF files.")
        return successful_merges

    except Exception as e:
        print(f"Error during PDF merge operation: {e}")
        return []


def preprocess_pdf(pdf_path, pages_to_drop_from_end=0, pages_to_drop_from_start=0,
                   specific_pages_to_keep=None, specific_pages_to_exclude=None):
    """
    Preprocess a PDF by removing specified pages.

    Parameters:
    pdf_path (str): Path to the input PDF file
    pages_to_drop_from_end (int): Number of pages to drop from the end
    pages_to_drop_from_start (int): Number of pages to drop from the start
    specific_pages_to_keep (list): List of page numbers to keep (1-indexed), ignores other parameters
    specific_pages_to_exclude (list): List of page numbers to exclude (1-indexed)

    Returns:
    PdfReader: Modified PDF reader object, or None if processing failed
    """
    try:
        reader = PdfReader(str(pdf_path))

        # Handle encryption
        if reader.is_encrypted:
            if not reader.decrypt(''):
                print(f"    Warning: {pdf_path.name} is encrypted and cannot be decrypted")
                return None

        total_pages = len(reader.pages)

        if total_pages == 0:
            print(f"    Warning: {pdf_path.name} has no pages")
            return None

        # Determine which pages to keep
        if specific_pages_to_keep:
            # Use specific pages (1-indexed)
            pages_to_keep = [p - 1 for p in specific_pages_to_keep if 1 <= p <= total_pages]
        elif specific_pages_to_exclude:
            # Exclude specific pages (1-indexed)
            pages_to_exclude = [p - 1 for p in specific_pages_to_exclude if 1 <= p <= total_pages]
            pages_to_keep = [i for i in range(total_pages) if i not in pages_to_exclude]
        else:
            # Drop from start/end
            start_page = pages_to_drop_from_start
            end_page = total_pages - pages_to_drop_from_end

            if start_page >= end_page:
                print(
                    f"    Warning: {pdf_path.name} would have no pages left after dropping {pages_to_drop_from_start} from start and {pages_to_drop_from_end} from end")
                return None

            pages_to_keep = list(range(start_page, end_page))

        if not pages_to_keep:
            print(f"    Warning: {pdf_path.name} would have no pages left after preprocessing")
            return None

        # Create new PDF with selected pages
        writer = PdfWriter()
        for page_num in pages_to_keep:
            if 0 <= page_num < total_pages:
                writer.add_page(reader.pages[page_num])

        print(f"    Preprocessed {pdf_path.name}: kept {len(pages_to_keep)}/{total_pages} pages")
        return writer

    except Exception as e:
        print(f"    Error preprocessing {pdf_path.name}: {e}")
        return None

# just to track a change
def compress_pdf(input_pdf: str, output_pdf: str, dpi: int = 200, jpeg_quality: int = 80, grayscale: bool = False):
    """Compress a scanned PDF into a smaller file while keeping legibility."""

    def human(n: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if n < 1024.0:
                return f"{n:3.1f} {unit}"
            n /= 1024.0
        return f"{n:.1f} TB"

    src = fitz.open(input_pdf)
    out = fitz.open()
    try:
        # Copy metadata
        try:
            out.set_metadata(src.metadata or {})
        except Exception:
            pass

        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)

        for i in range(len(src)):
            page = src.load_page(i)
            pm = page.get_pixmap(matrix=mat, alpha=False)
            if grayscale:
                pm = fitz.Pixmap(fitz.csGRAY, pm)

            jpeg_bytes = pm.pil_tobytes(format="JPEG", optimize=True, quality=jpeg_quality)
            new_page = out.new_page(width=page.rect.width, height=page.rect.height)
            new_page.insert_image(page.rect, stream=jpeg_bytes)

        out.save(output_pdf, garbage=4, deflate=True)
    finally:
        out.close()
        src.close()

    in_size = os.path.getsize(input_pdf)
    out_size = os.path.getsize(output_pdf)
    print(f"Done. Input: {human(in_size)} → Output: {human(out_size)}")


if __name__ == "__main__":

    pdf_handler_choice = 2

    if pdf_handler_choice == 1:
        # Run the function to compress a PDF
        compress_pdf("pdfs/Tab 6 - Skandia/Tradução certificada - Skandia.pdf",
                     "pdfs/Tab 6 - Skandia/Tradução certificada 2 - Skandia.pdf",
                     dpi=150,
                     jpeg_quality=75,
                     grayscale=True)


    elif pdf_handler_choice == 2:
        # Run the function to merge
        result = merge_pdfs_by_subdirectory()
        if result:
            print(f"\nMerged PDF files created:")
            for file_path in result:
                print(f"  - {file_path}")
        else:
            print("No PDF files were merged.")


    elif pdf_handler_choice == 3:
        # Run the function to strip pages from input PDFs:
        pdfs_dir = Path.cwd() / "pdfs"
        pdf_list = list(pdfs_dir.glob("*.pdf"))
        for pdf in pdf_list:
            newfile = preprocess_pdf(pdf, pages_to_drop_from_end=1)
            try:
                with open(pdf, 'wb') as output_file:
                    newfile.write(output_file)

                newfile.close()

            except Exception as e:
                print(f"  Error writing merged file for '{pdf}': {e}")
                newfile.close()
                continue

    else:
        print("Invalid choice. Exiting.")
