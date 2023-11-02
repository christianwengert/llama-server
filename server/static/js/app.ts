import hljs from "highlight.js";
import 'highlight.js/styles/github-dark.css';


const scrollToBottom = () => {
    let messages = document.getElementById("chat")!
    messages.scrollTo(0, messages.scrollHeight);
}

const getFormDataAsJSON = (formId: string): Record<string, string | number | boolean> => {
    const form = document.getElementById(formId) as HTMLFormElement;
    const formData: Record<string, string | number | boolean> = {};

    if (form) {
        for (const [key, value] of new FormData(form).entries()) {
            if (value === 'true') {
                formData[key] = true;
            } else if (value === 'false') {
                formData[key] = false;
            } else if (value !== "" && !isNaN(Number(value))) {
                // @ts-ignore
                formData[key] = parseFloat(value);
            } else {
                formData[key] = value.toString();
            }
        }
    }

    return formData;
};


const round = (originalNumber: number, digits: number) => {
    const t = 10 ** digits;
    return Math.round(originalNumber * t) / t;
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


const setFocusToInputField = (textInput: HTMLDivElement) => {
    if (textInput) {
        setTimeout(() => {
            textInput.focus()
        }, 200)
    }
};


const setupUploadButton = () => {
    const uploadButton = document.getElementById('upload-button')
    if (uploadButton) {
        uploadButton.addEventListener('click', (e) => {
            e.preventDefault();

            const formElement = document.getElementById("upload-form") as HTMLFormElement;

            // Create a new FormData object
            const formData = new FormData(formElement);

            fetch("/upload",
                {
                    body: formData,
                    method: "post"
                }).then(() => {
                // window.location.href = '/embeddings/' + name;
                console.log('upload done')
                document.location.hash = ''
            });

        })
    }
};

const loadHistory = () => {
    type Message = {
        role: string;
        content: string;
    }

    type HistoryItem = {
        url: string;
        title: string;
        items: Array<Message>;
        assistant: string;
        user: string;
    };
    type HistoryItems = HistoryItem[];
    const historyDiv = document.getElementById('history') as HTMLUListElement;
    historyDiv.innerHTML = "";
    const setHistory = (items: HistoryItems) => {

        items.forEach(item => {
            const liElement = document.createElement('li');
            const aElement = document.createElement('a');
            aElement.href = item.url;
            aElement.textContent = item.title;
            liElement.appendChild(aElement);
            historyDiv.appendChild(liElement);
            if(document.location.pathname.indexOf(item.url) >= 0) {
                renderHistoryMessages(item)
            }
        });
    }
    const chat = document.getElementById('chat')!;

    const renderHistoryMessages = (item: HistoryItem) => {

        if(chat.children.length > 0) {
            return;  // not necessary to do anything, it is rendered already
        }

        item.items.forEach((msg, index) => {
            const direction = index % 2 === 0 ? "me" : "them";
            renderMessage(msg.content, direction, chat)
        })
    }
    const index = document.location.pathname.indexOf('/c/')
    let url = '/history'
    if(index >= 0) {
        url += '/' + document.location.pathname.slice(index + 3)  // 3 is length of '/c/'
    }
    fetch(url).then((r) => r.json()).then(setHistory)
};
const run = () => {

        const chat = document.getElementById('chat')!;
        const stopButton = document.getElementById('stop-generating')! as HTMLButtonElement;
        if (stopButton) {
            stopButton.disabled = true;
        }

        setupUploadButton()

        const textInput = document.getElementById('input-box')! as HTMLDivElement;
        if (textInput) {
            textInput.addEventListener('keypress', handleInput)
        }

        function handleInput(e: KeyboardEvent) {
            if (e.key === 'Enter' && e.shiftKey === false) {
                e.preventDefault();
                const xhr = new XMLHttpRequest();
                const m = textInput.innerText;
                renderMessage(textInput.innerText, 'me', chat);
                textInput.innerText = '';
                // textInput.contentEditable = "false";

                if (stopButton) {
                    stopButton.addEventListener('click', (e) => {
                        e.preventDefault();
                        xhr.abort();
                        stopButton.disabled = true;
                    })
                }

                stopButton.disabled = false;

                const ident = renderMessage('', 'them', chat)
                const elem = document.getElementById(ident)!;
                const inner = elem.querySelector('.inner-message')! as HTMLElement;
                inner.innerHTML = '<div class="loading"></div>'

                scrollToBottom()

                xhr.open('POST', '/');

                let buffer = '';
                let lastBufferLength = 0; // Keep track of how much we've read

                xhr.onprogress = function () {
                    const newText = xhr.responseText.substring(lastBufferLength);
                    buffer += newText;
                    lastBufferLength = xhr.responseText.length; // Update our progress

                    let start = 0, end = 0;
                    let separator = "~~~~";
                    while ((end = buffer.indexOf(separator, start)) !== -1) {
                        let message = buffer.substring(start, end);
                        start = end + separator.length; // skip past the delimiter

                        let jsonMessage;

                        jsonMessage = JSON.parse(message);

                        if (jsonMessage.stop === true) {
                            const timings = jsonMessage.timings
                            let model = jsonMessage.model
                            if (model) {
                                model = model.split('/').slice(-1);
                            }

                            const timing = document.getElementById('timing-info')! as HTMLSpanElement;
                            timing.innerText = `${round(timings.predicted_per_second, 1)} Tokens per second (${round(timings.predicted_per_token_ms, 1)}ms per token (${model})) `

                            textInput.contentEditable = "true";
                            stopButton.disabled = true;
                            // adapt markdown for ```
                            const pattern = /```([a-z]+)? ?([^`]*)```/g
                            const rep = `<div class="code-header"><div class="language">$1</div><div class="copy">Copy</div></div><pre><code class="language-$1">$2</code></pre>`
                            const intermediate = inner.innerText.replace(pattern, rep)
                            // adapt markdown for `
                            const pattern2 = /`([^`]*)`/g
                            const rep2 = `<code class="inline">$1</code>`
                            inner.innerHTML = intermediate.replace(pattern2, rep2)

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
                            break;
                        } else {
                            if(inner.innerText === "") {
                                jsonMessage.content = jsonMessage.content.trim();
                            }
                            inner.innerText += jsonMessage.content;
                        }

                    }
                    buffer = buffer.substring(start); // Remove parsed messages from the buffer
                };

                xhr.addEventListener("error", function (e) {
                    console.log("error: " + e);
                });

                xhr.onload = function() {
                    loadHistory()
                }
                xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");

                const formData = getFormDataAsJSON('settings-form')
                formData.input = m
                // @ts-ignore
                formData.stop = formData.stop.split(',')

                xhr.send(JSON.stringify(formData));


            }
        }

        setFocusToInputField(textInput);

        loadHistory()
    }
;


document.addEventListener('keydown', function (event) {
    // close popups on escape key
    if (event.key === 'Escape') {
        // Remove the hash from the URL to close the element opened via CSS anchors
        window.location.hash = '';
    }
});


run()
