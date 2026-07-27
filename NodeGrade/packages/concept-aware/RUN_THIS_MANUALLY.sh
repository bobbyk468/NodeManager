#!/bin/bash
# Run this script manually to complete Paper 2 PDF compilation
# This script requires entering your password for TeX installation

set -e

echo "======================================"
echo "Paper 2 Final Compilation Script"
echo "======================================"
echo ""

# Step 1: Install TeX
echo "Step 1: Installing BasicTeX (requires password)..."
echo "You will be prompted for your password."
echo ""

brew install basictex

echo ""
echo "✓ TeX installed successfully"
echo ""

# Step 2: Update PATH for current session
echo "Step 2: Updating PATH..."
eval "$(/usr/libexec/path_helper)"
echo "✓ PATH updated"
echo ""

# Verify pdflatex is available
if ! which pdflatex > /dev/null 2>&1; then
    echo "⚠ Warning: pdflatex not found. Trying alternate paths..."
    export PATH="/usr/local/texlive/2024/bin/x86_64-linux:/usr/local/texlive/2024/bin/universal-darwin:$PATH"
fi

echo "Step 3: Verifying pdflatex installation..."
which pdflatex
echo "✓ pdflatex found"
echo ""

# Step 4: Navigate to paper directory
cd /Users/brahmajikatragadda/Desktop/PHD/NodeGrade/NodeManager/NodeGrade/packages/concept-aware

echo "Step 4: Running PDF compilation (pass 1 of 2)..."
echo "This will take 30-60 seconds..."
echo ""

pdflatex -interaction=nonstopmode docs/paper_phase2_vis2027.tex > /tmp/pdflatex1.log 2>&1

if grep -q "Output written" /tmp/pdflatex1.log; then
    echo "✓ First pass completed successfully"
else
    echo "⚠ First pass completed (may have warnings)"
fi
echo ""

echo "Step 5: Running PDF compilation (pass 2 of 2 - resolves references)..."
pdflatex -interaction=nonstopmode docs/paper_phase2_vis2027.tex > /tmp/pdflatex2.log 2>&1

if grep -q "Output written" /tmp/pdflatex2.log; then
    echo "✓ Second pass completed successfully"
else
    echo "⚠ Second pass completed"
fi
echo ""

# Step 6: Verify PDF was created
echo "Step 6: Verifying PDF creation..."
if [ -f "docs/paper_phase2_vis2027.pdf" ]; then
    SIZE=$(ls -lh docs/paper_phase2_vis2027.pdf | awk '{print $5}')
    echo "✓ PDF successfully created: $SIZE"
    echo ""
    echo "File: docs/paper_phase2_vis2027.pdf"
else
    echo "✗ PDF not found - compilation may have failed"
    echo "Check log: cat /tmp/pdflatex2.log"
    exit 1
fi
echo ""

# Step 7: Final verification
echo "Step 7: Final verification..."
echo ""

if file docs/paper_phase2_vis2027.pdf | grep -q "PDF"; then
    echo "✓ PDF is valid"
else
    echo "⚠ PDF validation failed"
fi

# Count figures in PDF
if which pdfimages > /dev/null 2>&1; then
    IMG_COUNT=$(pdfimages -list docs/paper_phase2_vis2027.pdf 2>/dev/null | tail -n +2 | wc -l)
    echo "✓ Images embedded in PDF: $IMG_COUNT"
fi

echo ""
echo "======================================"
echo "✓✓✓ COMPILATION COMPLETE ✓✓✓"
echo "======================================"
echo ""
echo "Next step: Open the PDF and visually verify all figures appear"
echo ""
echo "Command: open docs/paper_phase2_vis2027.pdf"
echo ""
