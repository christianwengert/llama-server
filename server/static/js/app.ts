import hljs from "highlight.js";
import 'highlight.js/styles/github.css';


const scrollToBottom = () => {
    let messages = document.getElementById("chat")!
    messages.scrollTo(0, messages.scrollHeight);
}


const renderMessage = (message: string, direction: 'me' | 'them', chat: HTMLElement): string => {
    const ident = (Math.random() + 1).toString(36).substring(2);
    const m = `
    <div class="message from-${direction}" id="${ident}">
        <div class="inner-message">${message}</div>
    </div>`
    chat.insertAdjacentHTML('beforeend', m);
    return ident;
};

const setupModelChange = () => {
    let modelChangeSelect = document.getElementById('model-change')! as HTMLSelectElement;
    modelChangeSelect!.addEventListener('change', ()=> {
        document.location = '/?' + new URLSearchParams({
            model: modelChangeSelect.value
        })
    })
    const p = new URLSearchParams(document.location.search)
    if (p.get('model')) {
        modelChangeSelect.value = p.get('model') || ""
    }
};


const setFocusToInputField = (textInput: HTMLDivElement) => {
    setTimeout(() => {
        textInput.focus()
    }, 100)
};

const run = () => {
    setupModelChange();

    // todo: We cannot stop generation yet
    const stopButton = document.getElementById('stop-generating')! as HTMLButtonElement;
    stopButton.addEventListener('click', (e) => {
        e.preventDefault();
        console.log('X')
    })


    const chat = document.getElementById('chat')!;
    const textInput = document.getElementById('input-box')! as HTMLDivElement;


    setFocusToInputField(textInput);

    textInput.addEventListener('keypress', handleInput)

    function handleInput(e: KeyboardEvent) {
        if (e.key === 'Enter' && e.shiftKey === false) {
            e.preventDefault();
            const m = textInput.innerText;
            renderMessage(textInput.innerText, 'me', chat);
            textInput.innerText = '';
            textInput.contentEditable = "false";
            stopButton.disabled = false;

            const ident = renderMessage('', 'them', chat)
            const elem = document.getElementById(ident)!;
            const inner = elem.querySelector('.inner-message')! as HTMLElement;
            inner.innerHTML = '<div class="loading"></div>'

            scrollToBottom()

            const xhr = new XMLHttpRequest();
            xhr.open('POST', '/');

            let seenBytes = 0;
            xhr.onreadystatechange = function () {

                if (xhr.readyState == 3) {  // streaming
                    const newData = xhr.response.substring(seenBytes);
                    if (inner.querySelector('.loading')) {
                        inner.innerHTML = "";
                    }
                    inner.innerHTML += newData;
                    seenBytes = xhr.responseText.length;
                    // if (newData.indexOf("\n") >= 0) {
                    //     const pattern = /```([a-z]+)? ?([^`]*)```/g
                    //     const rep = `<div class="code-header"><div class="language">$1</div><div class="copy">Copy</div></div><pre><code class="language-$1">$2</code></pre>`
                    //     inner.innerHTML = inner.innerText.replace(pattern, rep)
                    // }


                }
                if (xhr.readyState == 4) {  // done
                    textInput.contentEditable = "true";
                    stopButton.disabled = true;
                    // adapt markdown
                    const pattern = /```([a-z]+)? ?([^`]*)```/g
                    const rep = `<div class="code-header"><div class="language">$1</div><div class="copy">Copy</div></div><pre><code class="language-$1">$2</code></pre>`
                    inner.innerHTML = inner.innerText.replace(pattern, rep)

                    scrollToBottom()
                    // highlight code
                    inner.querySelectorAll('pre code').forEach((block) => {
                        hljs.highlightElement(<HTMLElement>block);
                    });
                    // set up copy to clipboard buttons
                    inner.querySelectorAll('.code-header >.copy').forEach((copyElem) => {
                        copyElem.addEventListener('click', (copyEvent) => {
                            copyEvent.preventDefault();
                            const target = copyEvent.target! as HTMLElement;

                            const t = (target.parentElement!.nextElementSibling! as HTMLElement).innerText;
                            // Copy the text inside the text field
                            navigator.clipboard.writeText(t).then(() => {
                            });
                            target.innerText = 'Copied'
                            target.style.cursor = 'auto'

                            setInterval(() => {
                                target.innerText = 'Copy'
                                target.style.cursor = 'pointer'

                            }, 3000)
                        })
                    })

                    textInput.focus()
                }
            };

            xhr.addEventListener("error", function (e) {
                console.log("error: " + e);
            });
            xhr.send(m);
        }
    }
};

run()
