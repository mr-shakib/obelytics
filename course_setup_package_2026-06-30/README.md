# New Course Setup Package

This folder contains the files needed to prepare another course in Obelytics.

## Files

1. `01_course_import.xlsx`
   - Upload from the Courses bulk import dialog.
   - Required headers are red.
   - Replace the placeholder row before importing.

2. `02_student_import.xlsx`
   - Upload from the Students bulk import page.
   - Email is optional.
   - Required headers are red.

3. `03_enrollment_import.xlsx`
   - Upload from the section roster bulk import area.
   - Use this after students exist and the new course section is created.

4. `04_midterm_marks_import.xlsx`
   - Placeholder Mid Term marks import structure.
   - After the section has real enrolled students and configured Mid Term questions, download the live template from the app so it contains the actual student IDs, names, question labels, and question marks.

5. `05_final_marks_import.xlsx`
   - Placeholder Final Exam marks import structure.
   - After the section has real enrolled students and configured Final Exam questions, download the live template from the app so it contains the actual student IDs, names, question labels, and question marks.

6. `06_course_customization_planning.xlsx`
   - Planning workbook for COs, CO-PO/KP/CEP mappings, delivery plan, and question configuration.
   - These sheets are not direct bulk imports unless the app later adds import endpoints for those areas.

## Current Existing Course

The local database currently has:

- `CSE 311` - `Database Management System`

Use a different course code in `01_course_import.xlsx`.

## Typical Order

1. Import or create the course.
2. Add the course to the required curriculum/term/section.
3. Customize course outcomes, mappings, assessment pattern, and delivery plan.
4. Import or create students.
5. Enroll students in the section.
6. Configure Mid Term and Final Exam questions.
7. Download live Mid Term and Final marks templates from the app.
8. Fill marks and import them.
