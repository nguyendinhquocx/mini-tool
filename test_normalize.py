#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Vietnamese Normalization
"""
import sys
sys.path.insert(0, 'src')

from core.services.normalize_service import VietnameseNormalizer

def test_normalization():
    normalizer = VietnameseNormalizer()
    
    test_cases = [
        ('Báo cáo tháng 12 (FINAL).docx', 'bao cao thang 12 final.docx'),
        ('Hình ảnh đẹp nhất năm 2024!.jpg', 'hinh anh dep nhat nam 2024.jpg'),
        ('Tài liệu_quan#trọng***.pdf', 'tai lieu quan trong.pdf'),
        ('Nguyễn ĐINH qucs# File.txt', 'nguyen dinh qucs file.txt'),
        ('File (1).txt', 'file 1.txt')
    ]
    
    print("=== Vietnamese Normalization Test Results ===")
    passed = 0
    failed = 0
    
    for original, expected in test_cases:
        try:
            result = normalizer.normalize_filename(original)
            if result == expected:
                passed += 1
                status = "PASS"
            else:
                failed += 1
                status = "FAIL"
                
            print(f"[{status}]")
            print(f"  Original:  {repr(original)}")
            print(f"  Expected:  {repr(expected)}")
            print(f"  Got:       {repr(result)}")
            print("-" * 60)
            
        except Exception as e:
            failed += 1
            print(f"[ERROR]: {repr(original)}")
            print(f"  Exception: {str(e)}")
            print("-" * 60)
    
    print(f"Test Summary: {passed} passed, {failed} failed")
    return failed == 0

if __name__ == "__main__":
    success = test_normalization()
    sys.exit(0 if success else 1)