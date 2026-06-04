# OBE Accreditation Management Platform

## Functional Requirements Document (FRD) v1.0

### Project Overview

The OBE Accreditation Management Platform is a web-based system designed to manage Outcome-Based Education (OBE), curriculum planning, program outcome mapping, attainment calculation, assessment management, and accreditation reporting for higher education institutions.

The system will support configurable roles, permissions, curriculum versions, accreditation workflows, attainment analysis, and report generation.

---

# 1. SYSTEM OBJECTIVES

The platform shall:

* Manage institutional academic structures
* Support Outcome-Based Education (OBE)
* Support accreditation requirements
* Manage curriculum versions
* Manage Program Outcomes (PO)
* Manage Course Outcomes (CO)
* Support CO-PO Mapping
* Support CO-CP Mapping
* Support CO-CA Mapping
* Support CO-KP Mapping
* Calculate attainment
* Generate accreditation reports
* Provide role-based access control (RBAC)
* Maintain audit trails
* Support future expansion without code changes

---

# 2. USER ROLES

## 2.1 Super Admin

Highest authority in the system.

Responsibilities:

* Manage organizations
* Manage departments
* Manage programs
* Manage users
* Manage roles
* Manage permissions
* Manage system configuration
* View all reports
* View audit logs
* Create custom roles

---

## 2.2 Program Coordinator

Program-level administrator.

Example:

B.Sc. in CSE Coordinator

Responsibilities:

* Manage curriculum
* Manage batches
* Manage program outcomes
* Manage course outcomes
* Manage mappings
* Manage attainment configurations
* Approve academic workflows
* Generate reports

---

## 2.3 Module Leader

Course-level authority.

Responsibilities:

* Manage assigned courses
* Review assessments
* Approve marks
* Approve attainment calculations
* Review CO mappings

---

## 2.4 Section Teacher

Course delivery role.

Responsibilities:

* Manage attendance
* Enter marks
* Conduct assessments
* View student performance
* Submit attainment data

---

## 2.5 Student

Responsibilities:

* View curriculum
* View courses
* View attendance
* View results
* View profile

---

# 3. ROLE & PERMISSION MANAGEMENT

The platform shall implement RBAC.

Entities:

User
Role
Permission

Relationships:

User → Multiple Roles

Role → Multiple Permissions

Permissions Examples:

user.create
user.update
user.delete

program.create
program.update

curriculum.create

report.generate

attainment.view

Future roles must be created without requiring code modifications.

---

# 4. CONFIGURATION MODULE

## 4.1 Organization Information

Fields:

* Organization Name
* Short Name
* Description
* Vision
* Mission
* Logo
* Website
* Address
* Contact Email
* Contact Phone

Operations:

* Create
* Update
* View

Only one active organization per deployment.

---

## 4.2 Department Management

Fields:

* Department Name
* Department Short Name
* Head of Department
* Year Established
* Description
* Vision
* Mission

Operations:

* Create
* Edit
* Archive

---

## 4.3 Program Management

Fields:

* Program Title
* Program Acronym
* Program Type
* Department
* Minimum Duration
* Total Credits
* Study Mode
* Description

Program Types:

* Undergraduate
* Postgraduate
* PhD

Study Modes:

* Full Time
* Part Time

Operations:

* Create
* Edit
* Archive

---

## 4.4 User Management

Faculty Fields:

* Faculty Type
* Title
* First Name
* Last Name
* Email
* Contact Number
* Department
* Designation
* Role Assignment

Password Options:

* Manual Entry
* Auto Generate

Operations:

* Create
* Edit
* Deactivate
* Reset Password

Email validation shall support configurable regex patterns.

---

## 4.5 Program Outcome (PO) Management

Default:

PO1–PO12

Fields:

* PO Code
* PO Reference
* PO Statement
* PO Type
* Bloom Domain
* Attributes
* Knowledge Profiles

Operations:

* Create
* Edit
* Archive

Deletion prohibited if linked to curriculum data.

---

## 4.6 Complex Problems (CP)

Fields:

* CP Code
* Description

Operations:

* Create
* Edit
* Archive

---

## 4.7 Complex Activities (CA)

Fields:

* CA Code
* Description

Operations:

* Create
* Edit
* Archive

---

## 4.8 Knowledge Profiles (KP)

Fields:

* KP Code
* Description

Operations:

* Create
* Edit
* Archive

---

## 4.9 Course Types

Examples:

* Theory
* Lab
* Project
* Thesis
* Internship

Operations:

* Create
* Edit
* Archive

---

## 4.10 Delivery Methods

Examples:

* Lecture
* Demonstration
* Brainstorming
* Discussion
* Group Work
* Presentation

Operations:

* Create
* Edit
* Archive

---

## 4.11 Sessional Types

Examples:

* Quiz
* Assignment
* Project
* Presentation
* Viva

Operations:

* Create
* Edit
* Archive

---

## 4.12 Bloom Domains

Default:

* Cognitive
* Affective
* Psychomotor

Operations:

* Create
* Edit

---

## 4.13 Bloom Levels

Examples:

C1 Remember

C2 Understand

C3 Apply

C4 Analyze

C5 Evaluate

C6 Create

Operations:

* Create
* Edit

---

## 4.14 Mapping Weight Distribution

Default:

1 = Low

2 = Medium

3 = High

Operations:

* Configure
* Update

---

# 5. CURRICULUM MANAGEMENT MODULE

## 5.1 Curriculum

Fields:

* Curriculum Name
* Curriculum Code
* Program
* Effective Year
* Status

Examples:

B.Sc. in CSE 2026

Operations:

* Create
* Edit
* Archive
* Version

Multiple curriculum versions must coexist.

---

## 5.2 Academic Terms

Examples:

Semester 1

Semester 2

Semester 3

Operations:

* Create
* Edit

---

## 5.3 Course Management

Fields:

* Course Code
* Course Title
* Credits
* Theory Hours
* Lab Hours
* Course Type
* Description

Operations:

* Create
* Edit
* Archive

---

## 5.4 Course Prerequisites

Fields:

* Parent Course
* Prerequisite Course

Operations:

* Add
* Remove

---

## 5.5 Batch Management

Fields:

* Batch Name
* Curriculum
* Intake Date
* Graduation Year

Examples:

Batch 66

Batch 67

Operations:

* Create
* Edit
* Archive

---

# 6. COURSE OUTCOME MANAGEMENT

## 6.1 Course Outcomes

Fields:

* CO Code
* Outcome Statement
* Bloom Level
* Delivery Methods

Operations:

* Create
* Edit
* Archive

Business Rule:

CO cannot be modified after attainment publication.

Status:

Draft
Approved
Published
Locked

---

## 6.2 CO-PO Mapping

Mapping Matrix

Values:

1
2
3

Operations:

* Create
* Edit
* Approve
* Publish

---

## 6.3 CO-CP Mapping

Operations:

* Create
* Edit
* Approve

---

## 6.4 CO-CA Mapping

Operations:

* Create
* Edit
* Approve

---

## 6.5 CO-KP Mapping

Operations:

* Create
* Edit
* Approve

---

# 7. ACADEMIC STRUCTURE MODULE

## Terms

Examples:

Spring 2026

Summer 2026

Fall 2026

---

## Sections

Examples:

Section A

Section B

Section C

---

## Faculty Assignment

Fields:

* Teacher
* Course
* Section
* Term

Operations:

* Assign
* Reassign
* Remove

---

# 8. ASSESSMENT MODULE

Assessment Types:

* Quiz
* Assignment
* Lab
* Midterm
* Final
* Project
* Presentation
* Viva

---

## Assessment Configuration

Fields:

* Assessment Name
* Assessment Type
* Total Marks
* Weightage

---

## Assessment-CO Mapping

Operations:

* Create
* Edit

---

## Marks Entry

Section teachers shall:

* Enter marks
* Update marks before publication

---

## Result Publication

Workflow:

Teacher
→ Module Leader
→ Program Coordinator

---

# 9. ATTAINMENT MODULE

## Threshold Configuration

Examples:

60%

65%

70%

---

## CO Attainment

System calculates:

CO-wise attainment

---

## Course Attainment

System calculates:

Course-wise attainment

---

## PO Attainment

System calculates:

Program-wise attainment

---

## Trend Analysis

Reports:

* Semester-wise
* Batch-wise
* Year-wise

---

# 10. REPORTS MODULE

Report Categories:

* Curriculum Reports
* Course Reports
* CO Reports
* PO Reports
* Mapping Reports
* Assessment Reports
* Attainment Reports
* Faculty Reports
* Batch Reports
* Accreditation Reports

Export Formats:

* PDF
* Excel
* CSV

---

# 11. AUDIT LOG MODULE

The system shall track:

* User
* Action
* Timestamp
* Old Value
* New Value

Examples:

Created Curriculum

Updated PO Mapping

Published Results

Deleted Course

---

# 12. NOTIFICATION MODULE

Notifications:

* Approval Requests
* Assessment Publication
* Result Publication
* Mapping Approval
* Attainment Completion

Delivery:

* In-App
* Email

---

# 13. APPROVAL WORKFLOW

Workflow States:

Draft

Submitted

Under Review

Approved

Rejected

Published

Locked

Approval Chain:

Section Teacher
→ Module Leader
→ Program Coordinator

---

# 14. NON-FUNCTIONAL REQUIREMENTS

Performance:

* Dashboard load < 2 seconds
* API response < 500ms average

Security:

* JWT Authentication
* Refresh Tokens
* RBAC Authorization
* Audit Logging

Scalability:

* Support multiple departments
* Support multiple programs
* Future multi-university support

Availability:

* Daily backups
* Disaster recovery support

Technology Stack:

Frontend: Next.js

Backend: FastAPI

Database: PostgreSQL

Cache: Redis

Storage: MinIO

Deployment: Docker + Nginx
