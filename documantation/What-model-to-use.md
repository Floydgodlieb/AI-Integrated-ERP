# What model to use?
To start working on developing the project we need to find the perfect model to use. We can do this by ranking the model based on our requirements for the models. 

## Model requirements
To find the correct model we have all requirments that the model needs to have. These are based on the goal of this project:
- Self hosted.
- Shaped to do the desired task
- No calling limits
- Reach API's
- Intergrate in existing chat systems
- Free to use

## Models 
* **Anthropic**
Via teams we got a link shared about Claude Managed Agents. This is a quick and easy way to make a model used for productivity. This is done using claude console. To check it out I made a account.
* **LocalAI**
This is a free and open source alternative of **Anthropic** and claims to have `No cloud, no limits, no compromise.`
* **ollama**

According to recent research[^1], the implementation shows promising results.

[^1]: Smith, J. A., & Johnson, M. B. (2024). *Advanced markdown processing techniques*. Journal of Documentation Science, 12(4), 234-248. https://doi.org/10.1000/example



## quick start
Quick start shows 4 steps on creating a model

- 1 Create agent
- 2 Configer enviorment
- 3 Start session
- 4 Intergrate

In the vidoe shared (https://www.youtube.com/watch?v=Ob5Vu-gD3mo) it shown that after giving the promt of what the model should do it start creating and testing it. My doubt is on if this comes with a price tag. I seen a screen where they want me to spend 5 euro.

After giving it a promt "I want a agent to work with a local hosted odoo.com ERP. The ERP has API endpoints to use. The idea is that a user can send a message about a sale that was made and this gets stored in the database using the ERP endpoint".

I got the message "Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.
You can send another message to try again, or edit the config directly."

The price is for API use. The chat bot on https://claude.com/pricing says "As a developer, you can access the Claude API for free with usage-based billing - you only pay for what you use.
The free tier includes access to Claude Sonnet 4.6 by default, plus file creation, connectors, skills, and compaction features. You can get started quickly using claude-sonnet-4-6 via the Claude API.
The Claude Developer Platform provides programmatic access to integrate Claude into your applications, with support for tools, file handling, and extended context management. This lets you build Claude's capabilities into your software, websites, or apps rather than just chatting with Claude directly.
You start with no upfront costs and only pay based on your actual API usage.
Fin AI Agent • Just now
Was this helpful?
Fin AI Agent • Just now"

As a student I can get acces to a limited Claude Sonnet 4.6. This might be able to do the trick.
The free alternative would be to use https://localai.io/ to get the same result witouth needing to pay for it.

# LocalAI
Local AI calls itself 'The free, OpenAI, Anthropic alternative.'. This makes it a prefect alternative for Anthropic. I'm going to look if this is the case. It must be free with no limitations.

