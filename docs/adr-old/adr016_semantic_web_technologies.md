# Use of semantic web technologies

Date: 2024-09-24

## Summary

In the context of **providing semantic meta-data as part of our website**

facing **a need for a good developer experience with good SEO outcomes**

we decided for **using a semantic HTML skeleton and dynamic JSON-LD for SEO**

and neglected **server-side rendering (SSR) as well as supporting older search engines fully**

to achieve **a faster migration to Angular with acceptable SEO outcomes**

accepting that **performance in older search engines and general no-js environments may suffer**.

## Details

### Status

**accepted**

### Context & Requirements

Using semantic HTML is a complete upgrade over not doing so. It is considered standard, [there is basically complete browser support](https://caniuse.com/html5semantic) and it has no technical downside.

JSON-LD allows us to offer JSON objects in the page that the search engines can use to understand the content. We can either generate these dynamically (i.e. components contribute data about their content as they get rendered) or the page can provide one static set independent of which page is rendered.

While the use of semantic HTML is easy, the use of useful JSON-LD is more complex since the content has to be generated separately from the basic website. Creating JSON-LD dynamically requires execution of JavaScript code, which isn't supported in older search engine crawlers. Only Google and Bing crawlers will execute JavaScript code and so the dynamic data model will only be available to them. In an environment where JavaScript execution is disabled, we could only provide JSON-LD that has been created at compile time. If we don't use SSR, these crawlers receive the same, nearly empty index.html file. As a consequence, they would see the same JSON-LD data on all pages which would not help to clarify the content of the pages or the information available there so we should not pursue this line of thought.

RDFa and Microdata are two other standards to incorporate data into the markup of a website to provide structured data to crawlers. The key difference is, that microdata and RDFa data is added to the elements where the content is also shown on the page as additional attributes, whereas JSON-LD is included in a separate tag in the page head. Using the head instead of the body keeps the two topics of visualizing data for the browser and providing meta-data for the crawlers separate, improving code readability. The data we want to provide as JSON-LD is also already available from the API requests in a JSON format that we can extend to be useful as the JSON-LD data, instead of mapping it to UI elements across (possibly) multiple UI components.

### Decision

Using semantic HTML tags is recommended, simple and has no downsides, so we will do it.

Covering all possibilities would require an effort that is not justified by the expected benefit. As a consequence, we have decided to neglect crawlers that don't execute JavaScript for now. We will therefore not use SSR (or SSG) and we can rely on the execution of JavaScript in the crawler to build the JSON-LD data dynamically. We should use this possibility to make the data easier to "understand" for the crawlers so our users can also find useful data with search engines. To this end, we will use a sitemap (we can add this after the launch of the Angular App) and dynamically generated JSON-LD. While this will exclude some older search engines from parsing our website successfully, it provides a reasonable balance between cost and benefit. We will also re-evaluate the search engine performance of the website, to see if this approach works.

We have decided not to use Microdata or RDFa because they would mix the markup rendered for the browser with the SEO optimization meta-data in the component code, although these are separate concerns.

### Consequences

This will not lead to optimal outcomes in old search engines. However, this option offers a good balance between ease of implementation and SEO outcomes since modern search engines interpret SPAs. At a later time, we can evaluate if some static site generation or other techniques are required for additional SEO improvements.

### Alternatives

We could use server side rendering without JSON-LD, making the website easy to parse for (older) search engines incurring higher development effort and infrastructure cost.
We could also use a server side technology to differentiate between crawlers/bots and browsers and deliver different content to crawlers. This would make testing more difficult and it would require a more complex deployment strategy and ops effort.
Another option would be to use html attributes (Microdata or RDFA) to expose meta-data for search engines instead of JSON-LD.
