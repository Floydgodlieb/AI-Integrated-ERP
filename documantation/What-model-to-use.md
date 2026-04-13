# What model to use?
To start working on developing the project we need to find the perfect model to use. We can do this by ranking the model based on our requirements for the models. 

## Model requirements
To find the correct model we have all requirement that the model needs to have. These are based on the goal of this project:

* Self hosted.
* customizable to do the desired task
* No calling limits
* Function Calling
* Integratable in existing chat systems (Teams)
* Free to use

## Model runners
* **Anthropic**
Via teams we got a link shared about Claude Managed Agents. This is a quick and easy way to make a model used for productivity. This is done using claude console. To check it out I made an account.
* **LocalAI**
This is a free and open source alternative of **Anthropic** and claims to have `No cloud, no limits, no compromise`.
* **ollama**
A offline optimized moddel running system that uses CLI and API to interact that focus on optimizatin instead of full fine-tuning of the models. [^1]
* **LM studio**
Focus on non technical users that uses JSON as output and able to work with REST API.

## Results

|                     | Anthropic | LocalAI | ollama | LM studio |
|---------------------|-----------|---------|--------|-----------|
| Self hosting        |    ❌       |  ✔️        |  ✔️       | ✔️           |
| customizable           |    ❌ system prompt       |      ✔️   |    ✔️    |    ❌ system prompt      |
| No limits (exc Token)          |    ❌       |   ✔️      |  ✔️      |  ✔️          |
| Function Calling	| ✔️  |	✔️ |	✔️ |	❌ |
| Teams Intergratable |     ✔️      |   ✔️      | ✔️ |   ❌        |
| Free                |    ❌     |   ✔️   |   ✔️     |    ✔️       |

## Final decision
The decision is made to use Ollama because it is easy to host, and its documentation is excellent

## Sources
[^1]: Tahir (24 Mar 2025). *💻What is Ollama: Running Large Language Models Locally*. medium. https://medium.com/@tahirbalarabe2/what-is-ollama-running-large-language-models-locally-e917ca40defe