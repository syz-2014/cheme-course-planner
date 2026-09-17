# COMS W2132 Intermediate Computing in Python, Final Project 
## <Chemical Engineering Course Table>

### Author:
- [Sophie Zhu](https://github.com/syz-2014) <syz2014@columbia.edu>
 
Replace the author name/email with your information.

## Project Category

Please select up to two items from the following list of categories that best describe your project:

* Web Application (full stack)
* Education, Tutoring or Learning Tool


Please select which type of application best describes your project:
* User-facing Web-app 


## Project Abstract 
I want to develop a web application that helps students in the Chemical Engineering major plan their coursework. The target users are undergraduate students who need to navigate complex degree requirements, including core courses, electives, prerequisites, and concentration tracks. Existing tools (such as static degree maps or PDFs) do not allow for flexible, personalized planning or real-time feedback. This application seeks to provide an interactive platform where students can build semester-by-semester schedules and immediately see how their choices affect progress toward graduation.

The system will be divided into three main components: a data layer, a validation engine, and a user interface. The data layer will store structured information about courses, prerequisites, credits, and requirement categories using JSON or CSV files. The validation engine will take a user’s planned schedule as input and output validation results, including prerequisite satisfaction, requirement completion status, and remaining requirements. Internally, prerequisite relationships will be modeled as a directed graph, and requirement tracking will use sets and dictionaries to efficiently compute progress. The user interface, built with Streamlit, will allow users to assign courses to semesters and visualize their plan and progress in real time.

The interaction between components is as follows: the user inputs a course plan through the interface → the plan is passed to the validation engine → the engine processes prerequisite constraints and requirement rules → results are returned to the interface and displayed as progress indicators and warnings. This modular design allows each component to be developed and tested independently.

To evaluate correctness, I will test the system using known valid and invalid course plans. For example, I will construct sample schedules that intentionally violate prerequisites or omit required courses and verify that the system correctly identifies these issues. I will also compare computed requirement progress against manually verified cases to ensure accuracy. AI tools may be used during development for code suggestions, debugging, and test case generation, but all core logic and system behavior will be implemented and understood by m

## Scope / Challenges

The initial scope of this project includes building a functional user-facing web application that allows students to build and modify semester-by-semester course plans, view progress toward the ChemE major and concentration requirements, and receive basic validation feedback such as unmet requirements. Core deliverables will include an interactive interface, a structured backend dataset of courses and requirements, and a rules engine that updates requirement counters as users adjust their schedules. 
Out of scope for the initial version are advanced features such as user authentication, cloud-based saving/loading of plans, integration with official university databases, and highly polished UI elements like drag-and-drop scheduling. 
The relatively straightforward components of the project are expected to be building the interface and structuring the course data, while the more challenging and uncertain aspects involve accurately encoding prerequisite logic, handling edge cases in degree requirements, and designing a flexible validation system that reflects actual school rules. 
Success for this project will be defined as delivering a working prototype that allows a user to construct a valid multi-semester plan and correctly tracks major requirement progress, even if some advanced features or edge cases are not fully implemented.

## Requirements / Dependencies 
On the software side, I plan to use Python along with common packages for building an interactive web app and organizing data, such as Streamlit for the user interface, pandas for handling course and requirement data, and possibly networkx or custom Python logic for representing prerequisite relationships. (Any advice or reccomendations would be appreciated!)
I may also use JSON or CSV files as the primary data source for course catalogs, degree requirements, and concentration rules. 

At this stage, I do not expect to need any specialized hardware beyond a standard laptop for development and testing. I also do not currently plan to rely on external online services or APIs, since the initial version can function using manually curated academic requirement data, although that could change later if I explore integration with official course information. 
In terms of AI usage, I expect to use AI mainly as a development aid for code generation, debugging, and testing support, such as helping draft functions, suggest interface ideas, and identify edge cases in the validation logic. I do not currently plan to make an LLM a core feature of the application itself, unless there is time (unlikely) to implement a course reccomendation feature, which will utilize AI. 

## Milestones 

During the first week, I will finalize the course dataset and requirement definitions, including prerequisite relationships and concentration requirements, and implement data loading functionality. During the second week, I will develop the validation engine, including prerequisite checking and requirement tracking, and test it using sample course plans. By April 26, I will complete a minimally viable product that includes a working interface for entering a course plan, basic prerequisite validation, and requirement progress tracking. During the third week, I will expand the Streamlit interface to improve usability and visualization, allowing users to interact more easily with their course plans. During the final week, I will focus on debugging, handling edge cases, and refining the presentation and overall user experience.

By April 26, the project will include a functional prototype that allows users to input a semester-by-semester course plan, view their progress toward major requirements, and receive feedback about missing prerequisites or unmet requirements. The system will correctly track completed and remaining requirements and provide clear output to the user.
