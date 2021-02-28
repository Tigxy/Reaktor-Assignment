# Reaktor Assignment (Summer 2021)
---

This is my implementation for the Reaktor Summer Junior Developer Assignment 2021. 


### Instructions (Source: [Reaktor](https://www.reaktor.com/junior-dev-assignment/))

>Your client is a clothing brand that is looking for a simple web app to use in their warehouses. To do their work efficiently, the warehouse workers need a fast and simple listing page per product category, where they can check simple product and availability information from a single UI. There are three product categories they are interested in for now: gloves, facemasks, and beanies. Therefore, you should implement three web pages corresponding to those categories that list all the products in a given category. One requirement is to be easily able to switch between product categories quickly. You are free to implement any UI you want, as long as it can display multiple products at once in a straightforward and explicit listing. At this point, it is not necessary to implement filtering or pagination functionality on the page.

>The client does not have a ready-made API for this purpose. Instead, they have two different legacy APIs that combined can provide the needed information. The legacy APIs are on critical-maintenance-only mode, and thus further changes to them are not possible. The client knows the APIs are not excellent, but they are asking you to work around any issues in the APIs in your new application. The client has instructed you that both APIs have an internal cache of about 5 minutes.



### About my implementation

It uses the Flask as web framework to display the products to the user. For keeping the data up to date, a separate thread that periodically updates the database with data retrieved from the APIs is used. As sharing an in-memory database across threads raises some problems, I have opted for using a SQLite database file that resides in the same directory. The benefits of using a database will be clear once one introduces features such as ordering or searching through the products. Note: For in production use, one might opt for other databases instead.


### Possible improvements

- Add pagination to reduce page loading times
- Add filtering / searching optionality for improved user experience
- Since the updating thread continiously locks the database to store data: If a lot of users will be using the website, a different approach for handling the data might be necessary. Otherwise, timeouts for reading from / writing to the database might occur.


### Update cycle

From the instructions we know that the APIs have an internal cache of about 5 minutes. Therefore, requesting data from the APIs more often than every 5 minutes might be pointless as the data will not have changed. This update interval and further settings can be changed via the [config.json](./config.json) file.


### Average execution times
As the APIs are quite slow and always transfer all the data that is available to them, the average time of each update step is quite long. Failures of requests, which result in a new request, are ignored. On average, each category API call takes 3.5s, while it takes 5s to update the database. The average duration of an manufacturer API call is 16s, where its update only takes 1s.

**Single category update**

- API call: 3.5s
- DB update: 5s

The reason why the DB update takes so long is that we currently update all but the ID and manufacturer column.

**Single manufacturer update**

- API call: 16s
- DB update: 1s

As we currently have 3 categories and usually 6 manufacturers, this results in a total average time of about **130s** for a single update cycle.

### Link
Current link to website:
[https://reaktor-junior-assignment.herokuapp.com/](https://reaktor-junior-assignment.herokuapp.com/)
