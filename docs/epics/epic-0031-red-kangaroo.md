# Angular/Vue for Data Portal (Red Kangaroo)

**Epic Type:** Exploratory Epic

Epic planning and implementation follow the Epic Planning and Marathon SOP.

## Principal Components of Exploration

This epic seeks to explore the use of Angular and Vue for a refactoring of the Data Portal (partly due to the deprecation of Create-React-App) by implementing some basic Metadata Catalog(ue) functionality on both frameworks and deciding on a potential framework for future refactoring.

### Questions to Answer

- Are any of the two options suitable for the development of the data portal?
- If so, which framework is best suited for the development of the data portal?
- Which framework's data handling system is best suited for the requirements of the data portal?
- Are Vue's advantages (e.g. shallower learning curve, less restrictive framework) enough of a positive to counter the lack of previous experience with it in the team?
- How are the overall development ergonomics?
  How many decisions do we have to make ourselves?
  How much structure is provided?

## Material and Resources

Materials to be studied (e.g. articles, book chapters, youtube videos, etc.) and any (external) persons/experts to talk to:

### React

- [React Documentation](https://react.dev/learn)
- [Next.js Documentation](https://nextjs.org/docs)
- [Remix Documentation](https://remix.run/docs/en/main)
- [React 18 for Beginners](https://codewithmosh.com/p/ultimate-react-part1) course (8h) by Mosh Hamedani
- [React - The Complete Guide 2023](https://www.udemy.com/course/react-the-complete-guide-incl-redux/) Udemy course (55h) by Maximilian Schwarzmüller

### Vue

- [Vue Documentation](https://vuejs.org/guide/introduction.html#introduction)
- [Vue.js Course for Beginners](https://www.youtube.com/watch?v=FXpIoQ_rT_c) on YouTube (3.5h) by Gwendolyn Faraday
- [Vue.js Tutorial: Beginner to Front-End Developer](https://www.youtube.com/watch?v=1GNsWa_EZdw) on YouTube (4h) by Jeremy McPeak
- [Vue 101 Crash Course](https://www.youtube.com/watch?v=IgBOT0QyByQ) on YouTube (6h) by Luis Ramirez
- [The Vue 3 Bootcamp - The Complete Developer Guide](https://www.udemy.com/course/the-vue-3-bootcamp-the-complete-developer-guide/) Udemy course (17.5h) by Laith Harb
- [Vue - The Complete Guide](https://www.udemy.com/course/vuejs-2-the-complete-guide/) Udemy course (31.5h) by Maximilian Schwarzmüller

### Angular

- [Angular Documentation](https://angular.io/docs)
- [Getting Started Tutorial](https://angular.io/start)
- [Learn RxJS](https://www.learnrxjs.io/)
- [Learn RxJS in 60 Minutes for Beginners](https://www.youtube.com/watch?v=PhggNGsSQyg) crash course on YouTube (1h) by Gary Simon
- [Angular for Beginners Course](https://www.youtube.com/watch?v=3qBXWUpoPHo) on YouTube (17.5h) by Santosh Yadav
- [Angular from Theory to Practice](https://codecraft.tv/courses/angular/) by Asim Hussain
- [Angular Fundamentals course](https://ultimatecourses.com/learn/angular-fundamentals) (5h) by Todd Motto
- [Angular 4: Beginner to Pro](https://codewithmosh.com/p/angular-master-class) course (30h) by Mosh Hamedani
- [Angular - The Complete Guide](https://www.udemy.com/course/the-complete-guide-to-angular-2/) Udemy course (36h) by Maximilian Schwarzmüller

## User Journeys (Optional)

This epic covers the following user journeys:

- The user views a list of all datasets
- The user filters the list of datasets based on facets provided by the API
- The user can see the summary of the details of the datasets the user selects.
- The user can see the full details of the datasets the user selects
- The user can submit a mock access request form

## Additional Implementation Details

- Although self-evident, it is important to specify the Metadata Catalog(ue) functionality will be implemented in both Angular and Vue.
- The implementation will require the development of a mock data service to examine the coding required for API calling in both Angular and Vue.
  This will add to the time required for development.

## Human Resource/Time Estimation

Number of sprints required: 3

Number of developers required: 1
