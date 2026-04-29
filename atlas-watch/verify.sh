#!/bin/bash
# Verification script for ATLAS Watch App

echo "=== ATLAS Watch App - Verification ==="
echo ""

echo "1. Checking directory structure..."
for dir in atlas-watch/source atlas-watch/resources/layouts atlas-watch/resources/strings atlas-watch/resources/drawables; do
    if [ -d "$dir" ]; then
        echo "   ✅ $dir/"
    else
        echo "   ❌ $dir/ MISSING"
    fi
done
echo ""

echo "2. Checking source files..."
for file in AtlasApp.mc AtlasView.mc DataManager.mc; do
    if [ -f "atlas-watch/source/$file" ]; then
        lines=$(wc -l < "atlas-watch/source/$file")
        echo "   ✅ source/$file ($lines lines)"
    else
        echo "   ❌ source/$file MISSING"
    fi
done
echo ""

echo "3. Checking config files..."
for file in manifest.xml monkey.jungle; do
    if [ -f "atlas-watch/$file" ]; then
        echo "   ✅ $file"
    else
        echo "   ❌ $file MISSING"
    fi
done
echo ""

echo "4. Checking resource files..."
for file in resources/strings/strings.xml resources/layouts/layout.xml; do
    if [ -f "atlas-watch/$file" ]; then
        echo "   ✅ $file"
    else
        echo "   ❌ $file MISSING"
    fi
done
echo ""

echo "5. Checking documentation..."
for file in README.md IMPLEMENTATION_SUMMARY.md; do
    if [ -f "atlas-watch/$file" ]; then
        echo "   ✅ $file"
    else
        echo "   ❌ $file MISSING"
    fi
done
echo ""

echo "6. Checking backend services..."
if [ -f "backend/app/services/readiness_service.py" ]; then
    lines=$(wc -l < "backend/app/services/readiness_service.py")
    echo "   ✅ readiness_service.py ($lines lines)"
else
    echo "   ❌ readiness_service.py MISSING"
fi

if [ -f "backend/app/api/api_v1/endpoints/readiness.py" ]; then
    lines=$(wc -l < "backend/app/api/api_v1/endpoints/readiness.py")
    echo "   ✅ readiness.py API ($lines lines)"
else
    echo "   ❌ readiness.py API MISSING"
fi
echo ""

echo "7. Checking frontend types..."
if grep -q "ReadinessResult" src/types.ts 2>/dev/null; then
    echo "   ✅ types.ts includes ReadinessResult"
else
    echo "   ❌ types.ts missing ReadinessResult"
fi

if grep -q "ReadinessDial" src/components/ReadinessDial.tsx 2>/dev/null; then
    echo "   ✅ ReadinessDial.tsx updated"
else
    echo "   ❌ ReadinessDial.tsx not found"
fi
echo ""

echo "=== Verification Complete ==="
