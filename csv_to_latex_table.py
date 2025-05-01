import os
import sys

import pandas as pd


def escape_latex(s):
    """Escape LaTeX special characters (excluding LaTeX commands) and replace underscores with spaces."""
    s = str(s)
    s = s.replace("_", " ")  # Replace underscores with spaces before escaping
    return (
        s.replace("&", "\\&")
        .replace("%", "\\%")
        .replace("$", "\\$")
        .replace("#", "\\#")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("~", "\\textasciitilde{}")
        .replace("^", "\\textasciicircum{}")
    )


def format_neurips_table(csv_path, output_path=None, caption=None, label=None):
    df = pd.read_csv(csv_path)

    # Capitalize column headers
    df.columns = [col.replace("_", " ").title() for col in df.columns]

    # Escape LaTeX characters and replace underscores with spaces in string cells
    df = df.applymap(lambda s: escape_latex(s) if isinstance(s, str) else s)

    # Format numeric columns (rounded to 0 decimals if int-like, 2 decimals otherwise)
    for col in df.select_dtypes(include=["float", "int"]).columns:
        if (df[col] == df[col].astype(int)).all():
            df[col] = df[col].apply(
                lambda x: f"{x / 1000:.2f}K" if abs(x) >= 1000 else f"{x:.0f}"
            )
        else:
            df[col] = df[col].apply(
                lambda x: f"{x / 1000:.2f}K" if abs(x) >= 1000 else f"{x:.2f}"
            )

    # Default output filename
    if output_path is None:
        base = os.path.splitext(os.path.basename(csv_path))[0]
        output_path = f"{base}_table.tex"

    # Default caption
    caption = "Default table caption"
    # Default label
    if label is None:
        label = (
            f"table:{os.path.splitext(os.path.basename(csv_path))[0].replace('-', '_')}"
        )

    # Convert to LaTeX tabular using booktabs with centered columns
    column_format = "l" * df.shape[1]
    latex_table = df.to_latex(
        index=False, escape=False, column_format=column_format
    )  # , booktabs=True)

    # Add indentation to the table lines for cleaner LaTeX code
    indented_table = "\n".join(
        "    " + line for line in latex_table.strip().splitlines()
    )

    # Wrap in full NeurIPS-style table environment
    wrapped = f"""\\begin{{table}}[htbp]
    \\caption{{{caption}}}
    \\label{{{label}}}
    \\centering
{indented_table}
\\end{{table}}"""

    with open(output_path, "w") as f:
        f.write(wrapped)

    print(f"✅ LaTeX table written to {output_path}")


# Entry point
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Usage: python csv_to_neurips_table.py path/to/input.csv [optional_output.tex]"
        )
        sys.exit(1)

    csv_input = sys.argv[1]
    output_tex = sys.argv[2] if len(sys.argv) > 2 else None
    format_neurips_table(csv_input, output_tex)
