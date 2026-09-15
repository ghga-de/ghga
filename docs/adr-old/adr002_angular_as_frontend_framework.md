# Angular as Frontend Framework

Date: 2024-01-09

## Summary

In the context of **the GHGA data portal single page application**

facing **the need for a frontend framework for development**

we decided for **using Angular**

and neglected **React, Vue and frameworks based on these**

to achieve **cleaner and less complex code and higher developer productivity**

accepting that **we need to move away from the currently used, very popular React based solution and re-implement the application**.

## Details

### Status

**accepted**

### Context & Requirements

The GHGA catalog and the first version of the GHGA data portal have been developed with the very popular React library and the "Create React App" tooling.

Contrary to our backend code, where we follow very strict coding guidelines and strive for a clean architecture, the frontend code has been developed in a less rigid fashion and became harder to maintain over time. This is in part because React is more a library than a full-fledged framework, so keeping a consistent structure is left to the team's own conventions. A more structured and opinionated framework could help us produce cleaner code and give us more guidance.

Another reason for reconsidering the usage of React was the discontinuation of the "Create React App" tooling and the official recommendation to use a framework like Next.js or Remix on top of React instead. This means we needed to learn a new framework and re-implement the application anyway, and not only in order to create cleaner code. Therefore it made sense to also consider different frameworks not based on React, particularly since the main advantages of the mentioned React-based frameworks lie in areas like SEO that are not so important for us. Yet another reason to think about Angular was a kind of "renaissance" of the framework in 2023 when standalone components, Signals, a new template control flow syntax and other new features were introduced with the goal of making the Angular framework even more performant and developer friendly.

The most popular and obvious alternatives to React were Angular, which qualifies as a frontend framework and not just a library, and Vue, which takes a kind of middle ground. So the decision to be made here was actually between Angular, and any framework or collection of libraries on top or React and Vue that would provide similar functionality.

We created a proof-of-concept re-implementation of core features of the GHGA catalog with Angular and Vue in order to get a feeling for how well these frameworks would support our needs. We also created a decision matrix with criteria explained in the appendix below. The matrix contains 15 differently weighted criteria for scores in the range of 0 to 5. When features were only available by using an extension framework or library, we deducted one or two points from our rating.

### Decision

The proof-of-concept and the decision matrix both showed a clear advantage of Angular over React and Vue. Therefore we propose to re-implement the GHGA data portal using Angular, and using Angular for implementing the frontends of future GHGA products.

### Consequences

The current developers are convinced that this change will result in cleaner, more readable and maintainable code, and increase developer productivity.

However, it could be slightly more difficult to onboard frontend developers, since React is more widely known. On the other hand, the re-implementation of the GHGA portal showed that as a frontend-developer it is not  too difficult to learn any of the other frameworks and to transfer the existing knowledge.

The re-write connected with the transition to Angular could also take longer than a re-write using a React-based framework. On the other hand, the re-write forces us to re-structure our code base more thoroughly.

### Alternatives

As alternatives to Angular, we considered React-based frameworks such as Next.js and Remix, as well as Vue or Vue-based frameworks such as Nuxt.js. We did not consider other frameworks like Svelte, Ember, Preact, Qwik, Solid, Mithril or jQuery, since they were less popular, outdated or limited in functionality. We also did not consider web components as an alternative to a full-fledged framework, since they only provide a limited part of the functionality of such a framework, and no guidance for structuring the code and connecting the components to form a complex application.

We consider React or Vue viable alternatives to Angular, but are confident that using Angular will result in more maintainable, standardized code and a better developer experience.

## Appendix: Evaluation Matrix

| Criterion | Weight | Angular | React | Vue |
| ---- | ---- | ---- | ---- | ---- |
| Completeness | 15% | 5 | 1 | 1 |
| Flexibility | 8% | 2 | 4 | 3 |
| Maturity | 8% | 5 | 4 | 3 |
| Popularity | 12% | 3 | 5 | 2 |
| Maintenance | 6% | 5 | 4 | 2 |
| Performance | 3% | 5 | 5 | 5 |
| Scalability | 3% | 5 | 5 | 4 |
| Ease of Learning | 6% | 4 | 4 | 3 |
| Documentation | 10% | 5 | 4 | 4 |
| Structuredness | 12% | 5 | 2 | 3 |
| Community | 5% | 4 | 5 | 3 |
| CLI and IDE support | 3% | 5 | 4 | 4 |
| Testing support | 3% | 4 | 3 | 3 |
| Security | 3% | 5 | 3 | 3 |
| Compatibility | 3% | 5 | 4 | 4 |
| Licensing | 0% | 5 | 5 | 5 |
| Internationalization | 0% | 4 | 3 | 4 |
| Total | 100% | 4,38 | 3,48 | 2,77 |

Remarks regarding the evaluated criteria:

We are aware that the list of criteria and weights is a bit arbitrary and ambiguous due to overlap, but we tried to base it on the concern for more structure, guidance and developer productivity, as explained above. We did not add the availability of UI component libraries and their quality as a criterion, because that would have gone beyond the scope of this evaluation and we do not expect huge differences between the frameworks in this regard. Instead, we decided to choose an appropriate component library after the selection of a framework.

We are aware that many of the assigned scores can be disputed. For a proper evaluation year-long experience with all three frameworks would be needed, which are continually evolving. This was just an attempt to quantify our current understanding which is naturally biased and limited. The ratings reflect the state of the three frameworks at the time of the evaluation and the specific needs of our project; they are not meant as a general ranking of these frameworks.

- Completeness:
	- Does the framework provide all essential features, like state management and routing? Does it also provide some non-essential, but important features like animations or server-side-rendering?
	- While Angular provides all of these features out of the box, React and Vue need additional libraries or extensions. This adds the burden of choice and makes the complete solution more complex to learn, maintain and update.
- Flexibility:
	- How easy is it to extend and customize the framework if necessary? Is it possible to change individual elements of the framework?
	- React and Vue are very flexible, since they provide only the core functionality, so custom extension is not only possible, but also necessary. Angular has much of this functionality already baked in, and deviating from the "prescribed" way is more difficult, but usually also not needed. However, Angular can also be extended with functionality like NgRx, a state management system.
- Maturity:
	- How mature and stable is the framework? How long is it available already? Have there been larger changes recently or are they to be expected?
	- Angular is used inside Google, and since the big transition to version 2, it is pretty stable. Updates are well-documented. React development is a bit more volatile, but generally React is also pretty stable and mature. At the time of the evaluation, Vue had recently introduced breaking changes with version 3, and its async functionality was split between vanilla JavaScript and an experimental feature.
- Popularity:
	- How popular is the framework? How widely used is it? How much support is available in the Internet? How easy is it to attract developers for this framework?
	- Here, React is clearly the most popular one and highly visible in the Internet, but Angular is also used by many companies.
- Maintenance:
	- How well is professional maintenance guaranteed in the long term? Is it backed by a large company?
	- Angular originated at Google and React at Meta (formerly Facebook), and both companies still act as primary maintainers together with the respective communities, each with a core development team of about 20 members. Google also collaborates with external supporters and Google developer experts. Vue started as an independent project and is maintained by a core team funded through its community rather than by a large company. Since this criterion asks specifically about long-term maintenance backed by a large organization, that difference is what the score reflects; it is not a statement about the quality of the projects.
- Performance:
	- How fast does the framework render the web pages? Does it provide optimizations for speed?
	- For all frameworks, there should be no performance bottleneck if the framework is used correctly.
- Scalability:
	- How well can the framework scale when projects become larger? Does it support modularization?
	- Angular explicitly supports modularization. All frameworks have been proven to scale to large and complex projects, though at the time of the evaluation we found more published guidance and tooling for scaling Angular and React to very large code bases than for Vue.
- Ease of learning:
	- How easy is it to learn using the framework?
	- It is often said that Angular has a more steep learning curve. However, this is mostly due to the fact that Angular includes more functionality. When using React, you need to learn additional libraries or frameworks. Other reasons for the perceived difficulty of learning Angular are its early support of TypeScript, and use of Reactive Extensions (RxJS). However, we consider TypeScript a necessity anyway. Reactive Extensions are highly useful even outside of Angular, while React hooks also have a learning curve and can not be used outside of React. The latest version of Angular also supports Signals which are easier to understand than Reactive Extensions. For Vue, a significant share of the community documentation and articles is published in Chinese rather than English. Since our team works in English, this reduced the learning material that was directly usable for us.
- Documentation:
	- This criterion measures the quality and completeness of the documentation for the framework. Clear and comprehensive documentation can save a lot of time and effort during development.
	- Generally, the documentation for all of the three frameworks is very good. Since Angular is a full-fledged framework, everything is documented in one place, which gives Angular a slight advantage here.
- Structuredness:
	- Does the framework support a clean architecture? Are there style and development guidelines? Does it support TypeScript and paradigms like Reactive extensions to make the code more structured and easier to understand? Does it support modularization?
	- How much does the framework guide developers to create clean and maintainable code?
	- The separation of template and code is best solved in Angular. Vue and React have them in one file, React even merges them via the JSX language. Angular has extensive coding and style guidelines. It also has a built-in dependency injection system, whereas React and Vue do not have such a system built-in. Data binding seems to be also more clear in Angular. The use of reactive programming in Angular can be challenging at first, but makes handling asynchronous data flows more manageable in the long run.
- Community support:
	- How large, active and supportive is the community around the framework? Are there conferences, Internet forums, podcasts?
	- The three projects all have large communities. While the React community is probably the largest one, Angular also has a large community, conferences, forums, podcasts etc. Vue has a particularly large and active community in China, so part of its forums, documentation and extension projects is primarily available in Chinese, which limited what our English-speaking team could draw on directly.
- CLI and IDE support:
	- Does the framework provide a CLI tool to support development? Are there plugins for Visual Studio Code supporting the framework? Are there developer tools that support debugging in the browser?
	- All frameworks are supported in Visual Studio Code and have developer tool extensions for the Chrome browser. Angular also has a powerful CLI tool to support development. Vue has a comparable tool with a somewhat smaller feature set. React itself has no CLI tool, but one is included in Next.js for instance.
- Testing:
	- How well does the framework support unit tests and integration tests?
	- Angular comes with support for unit and end-to-end tests, and the CLI tool also provides scaffolding for tests. Vue and React also provide test utilities, but Angular test environment may be a bit more comprehensive.
-  Security:
	- How well does the framework protect against common web security threats? Does it come with built-in security features?
	- Angular provides all important security features out of the box, while some security mechanisms like CSRF protection require additional libraries in React and Vue.
- Compatibility:
	- How well does the framework work with other tools and technologies? Can it use web components and wrap its own components as web components?
	- Angular has the most complete support for web components.
- Licensing
	- All three frameworks are MIT licensed, therefore we can ignore that criterion.
-  Internationalization:
	- Since we only plan to support English language, we can ignore this criterion as well.
