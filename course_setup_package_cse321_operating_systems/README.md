# CSE 321 Operating Systems - Complete Setup Package

This folder contains a complete, realistic setup package for a new course:

`CSE 321 - Operating Systems`

## Files

1. `00_package_index.xlsx`
   - Quick index of all files and where to use them.

2. `01_course_import.xlsx`
   - Directly importable from `Courses > Bulk Import`.
   - Creates `CSE 321 - Operating Systems`.
   - Required headers are red.

3. `02_student_import.xlsx`
   - Directly importable from `Students > Bulk Import`.
   - Contains 50 students with real names and email values.
   - Email remains optional in the system.
   - Required headers are red.

4. `03_enrollment_import.xlsx`
   - Directly importable from the section roster bulk import area.
   - Enrolls the same 50 students by student ID.

5. `04_midterm_marks_import.xlsx`
   - Filled Mid Term marks for all 50 students.
   - Columns include actual student IDs, full names, question labels, and max marks.

6. `05_final_marks_import.xlsx`
   - Filled Final Exam marks for all 50 students.
   - Columns include actual student IDs, full names, question labels, and max marks.

7. `06_course_customization_complete.xlsx`
   - Complete course customization workbook:
     - Course profile
     - Course objectives
     - Course outcomes
     - CO-PO mappings with justifications
     - KP and CEP mappings with justifications
     - Assessment pattern
     - Mid Term and Final question configuration
     - 14-week delivery plan
     - PO validation table

## Recommended Order

1. Import `01_course_import.xlsx`.
2. Add the course to the relevant curriculum and create a section offering.
3. Enter the details from `06_course_customization_complete.xlsx` in Course Customization.
4. Import students using `02_student_import.xlsx`.
5. Enroll students using `03_enrollment_import.xlsx`.
6. Configure Mid Term and Final questions using the question configuration sheet.
7. Import marks using `04_midterm_marks_import.xlsx` and `05_final_marks_import.xlsx`.

## Notes

- The existing database already contains `CSE 311 - Database Management System`; this package uses a different code, `CSE 321`.
- The marks files are filled and aligned with the question configuration in `06_course_customization_complete.xlsx`.
- If question labels or marks are changed inside the app, download a fresh live template before importing marks.
