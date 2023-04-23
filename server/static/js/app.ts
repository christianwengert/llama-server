import hljs from "highlight.js";
import 'highlight.js/styles/github-dark-dimmed.css';


function renderMessage(message: string, direction: 'me' | 'them', chat: HTMLElement): string {
    const ident = (Math.random() + 1).toString(36).substring(2);
    const m = `
    <div class="message from-${direction}" id="${ident}">
        <div class="inner-message">${message}</div>
    </div>`
    chat.insertAdjacentHTML('beforeend', m);
    return ident;
}

function run() {

    const chat = document.getElementById('chat')!;

    const textInput = document.getElementById('input-box')! as HTMLDivElement;
    textInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && e.shiftKey === false) {
            e.preventDefault();
            const m = textInput.innerText;
            renderMessage(textInput.innerText, 'me', chat);
            textInput.innerText = '';
            textInput.contentEditable = "false";

            const ident = renderMessage('', 'them', chat)
            const elem = document.getElementById(ident)!;
            const inner = elem.querySelector('.inner-message')! as HTMLElement;

            inner.innerHTML = "<span class=\"loading\"></span>";

            fetch(
                '/',
                {
                    method: "POST",
                    cache: "no-cache",
                    credentials: "same-origin",
                    headers: {
                        "Content-Type": "application/text",
                    },
                    body: m
                }
            ).then(async (response) => {
                response.text().then(answer => {
                    inner.innerHTML = answer;
                    textInput.contentEditable = "true";

                    inner.querySelectorAll('pre code').forEach((block) => {
                        hljs.highlightElement(<HTMLElement>block);
                    });

                    inner.querySelectorAll('.code-header >.copy').forEach((copyElem) => {
                        copyElem.addEventListener('click', (copyEvent) => {
                            copyEvent.preventDefault();
                            const target = copyEvent.target! as HTMLElement;

                            const t = (target.parentElement!.nextElementSibling! as HTMLElement).innerText;
                            // Copy the text inside the text field
                            navigator.clipboard.writeText(t);
                            target.innerText = 'Copied'
                            target.style.cursor = 'auto'

                            setInterval(() => {
                                target.innerText = 'Copy'
                                target.style.cursor = 'pointer'

                            }, 3000)
                        })
                    })
                })
            })
        }
    })
}

run()


