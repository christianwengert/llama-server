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


const handleEditAction = (e: MouseEvent) => {
    e.preventDefault()
    const target = e.target! as HTMLElement;
    const message = target.closest('.message')!;
    const inner = message.getElementsByClassName('inner-message')![0] as HTMLDivElement;
    // const messages = Array.from(target.closest('#chat')!.children)
    // const index = messages.indexOf(message);
    inner.contentEditable = "true";
    inner.focus()
    // Create a range
    const range = document.createRange();
    range.selectNodeContents(inner);

    // Get the selection object
    const selection = window.getSelection()!;

    // Clear all ranges
    selection.removeAllRanges();

    // Add the new range
    selection.addRange(range);
    inner.addEventListener('keypress', getInputHandler(inner))

}
//
// const handleVoteAction = (e: MouseEvent, index: 'up' | 'down') => {
//     e.preventDefault();
//     const target = e.target;
//     console.log(index, target)
// }
//
// const handleUpvoteAction = (e: MouseEvent) => {
//     handleVoteAction(e, 'up')
//
// };
// const handleDownvoteAction = (e: MouseEvent) => {
//     e.preventDefault();
//     handleVoteAction(e, 'down')
// };

const renderMessage = (message: string, direction: 'me' | 'them', chat: HTMLElement): string => {
    const ident = (Math.random() + 1).toString(36).substring(2);

    const messageDiv = document.createElement('div');
    messageDiv.className = `message from-${direction}`;
    messageDiv.id = ident;

    const innerMessageDiv = document.createElement('div');
    innerMessageDiv.className = 'inner-message';
    innerMessageDiv.textContent = message;
    messageDiv.appendChild(innerMessageDiv);

    if (direction === 'me') {
        const editButtonDiv = document.createElement('div');
        editButtonDiv.className = 'edit-button';
        const editLink = document.createElement('a');
        editLink.href = '/edit/';
        editLink.id = `edit-${ident}`;
        editLink.textContent = 'Edit';
        editButtonDiv.appendChild(editLink);

        editLink.addEventListener('click', handleEditAction)

        messageDiv.appendChild(editButtonDiv);
    } else {
        // const voteButtonDiv = document.createElement('div');
        // voteButtonDiv.className = 'edit-button';
        // const upvoteLink = document.createElement('a');
        // upvoteLink.href = '/upvote/';
        // upvoteLink.id = `upvote-${ident}`;
        // upvoteLink.textContent = '➞';
        // voteButtonDiv.appendChild(upvoteLink);
        //
        //
        // const downvoteLink = document.createElement('a');
        // downvoteLink.href = '/downvote/';
        // downvoteLink.id = `downvote-${ident}`;
        // downvoteLink.textContent = '➞';
        // voteButtonDiv.appendChild(downvoteLink);
        //
        // messageDiv.appendChild(voteButtonDiv);
        //
        // upvoteLink.addEventListener('click', handleUpvoteAction);
        // downvoteLink.addEventListener('click', handleDownvoteAction);
        //
        //
    }
    chat.appendChild(messageDiv);
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
            const li = document.createElement('li');
            const historyLink = document.createElement('a');
            const deleteButton = document.createElement('button');
            historyLink.href = item.url;
            historyLink.textContent = item.title;
            historyLink.className = "history-item-link";

            deleteButton.textContent = "×";
            deleteButton.className = "delete-history-item";
            deleteButton.addEventListener('click', (e) => {
                e.preventDefault()
                const url = `/delete/history/${item.url}`;
                fetch(url).then(() => {
                    if (document.location.pathname.indexOf(item.url) >= 0) {
                        // i deleted the current
                        document.location.pathname = '/';  // new session
                    } else {
                        loadHistory()
                    }
                })
            })

            li.appendChild(historyLink);
            li.appendChild(deleteButton);
            historyDiv.appendChild(li);
            if (document.location.pathname.indexOf(item.url) >= 0) {
                renderHistoryMessages(item)
            }
        });
    }
    const chat = document.getElementById('chat')!;

    const renderHistoryMessages = (item: HistoryItem) => {

        if (chat.children.length > 0) {
            return;  // not necessary to do anything, it is rendered already
        }

        item.items.forEach((msg, index) => {
            const direction = index % 2 === 0 ? "me" : "them";
            const ident = renderMessage(msg.content, direction, chat)

            const msgDiv = document.getElementById(ident)
            const inner = msgDiv!.getElementsByClassName('inner-message')[0] as HTMLElement;

            if (direction === 'them') {
                highlightCode(inner);
                setClipboardHandler(inner);
            }
        })
    }
    const index = document.location.pathname.indexOf('/c/')
    let url = '/history'
    if (index >= 0) {
        url += '/' + document.location.pathname.slice(index + 3)  // 3 is length of '/c/'
    }
    fetch(url).then((r) => r.json()).then(setHistory)
};

const removeAllChildrenAfterIndex = (parentElement: HTMLElement, index: number) => {
    // Assuming `parentElement` is the DOM element and `index` is the given index
    while (parentElement.children.length > index + 1) {
        parentElement.removeChild(parentElement.lastChild!);
    }
};

function highlightCode(inner: HTMLElement) {

    function convertMarkdownToHTML(mdString: string) {
        // Replace triple backtick code blocks
        const codeBlockRegex = /```([a-z]*)\n([\s\S]*?)```/g;
        mdString = mdString.replace(codeBlockRegex, (match, lang, code) => {
            const language = lang || 'bash';
            return `<div class="code-header"><div class="language">${language}</div><div class="copy">Copy</div></div><pre><code class="language-${language}">${escapeHTML(code)}</code></pre>`;
        });

        // Replace inline code
        const inlineCodeRegex = /`([^`]+)`/g;
        mdString = mdString.replace(inlineCodeRegex, '<code class="inline">$1</code>');

        return mdString;
    }

    function escapeHTML(str: string) {
        return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    const codeString = inner.innerText;

    inner.innerHTML = convertMarkdownToHTML(codeString);

    scrollToBottom()
    // highlight code
    inner.querySelectorAll('pre code').forEach((block: Element) => {
        hljs.highlightElement(block as HTMLElement);
    });
}

function setClipboardHandler(inner: HTMLElement) {
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
}

function getInputHandler(inputElement: HTMLElement) {

    const mainInput = document.getElementById('input-box')! as HTMLDivElement;
    let isMainInput = inputElement === mainInput;

    const chat = document.getElementById('chat')!;
    const stopButton = document.getElementById('stop-generating')! as HTMLButtonElement;
    if (stopButton) {
        stopButton.disabled = true;
    }

    let pruneHistoryIndex = -1;
    if (!isMainInput) {
        // a message has been edited, now remove the old ones
        const message = inputElement.closest('.message')!;
        const messages = Array.from(chat.children)
        pruneHistoryIndex = messages.indexOf(message);
        removeAllChildrenAfterIndex(chat, pruneHistoryIndex)
    }


    function handleInput(e: KeyboardEvent) {
        if (e.key === 'Enter' && e.shiftKey === false) {
            e.preventDefault();
            const xhr = new XMLHttpRequest();
            const m = inputElement.innerText;
            if (isMainInput) {
                renderMessage(inputElement.innerText, 'me', chat);
                inputElement.innerText = '';
            }
            inputElement.contentEditable = "false";
            inputElement.blur();

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

                    const jsonMessage = JSON.parse(message);

                    if (jsonMessage.stop === true) {
                        const timings = jsonMessage.timings
                        let model = jsonMessage.model
                        if (model) {
                            model = model.split('/').slice(-1);
                        }

                        const timing = document.getElementById('timing-info')! as HTMLSpanElement;
                        timing.innerText = `${model}: ${round(1000.0 / timings.predicted_per_token_ms, 1)} t/s `

                        // adapt markdown for ```
                        highlightCode(inner);
                        // set up copy to clipboard buttons
                        setClipboardHandler(inner);
                        inputElement.focus();
                        break;
                    } else {
                        if (inner.innerText === "") {
                            jsonMessage.content = jsonMessage.content.trim();
                        }
                        inner.innerText += jsonMessage.content;
                    }

                }
                buffer = buffer.substring(start); // Remove parsed messages from the buffer
                updateScrollButton();
            };

            xhr.addEventListener("error", function (e) {
                console.log("error: " + e);
            });

            xhr.onload = function () {
                if (isMainInput) {
                    inputElement.contentEditable = "true";
                }
                setFocusToInputField(mainInput);
                stopButton.disabled = true;
                loadHistory()
            }
            xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");

            const formData = getFormDataAsJSON('settings-form')
            formData.input = m

            // @ts-ignore
            formData.stop = formData.stop.split(',')
            formData.pruneHistoryIndex = pruneHistoryIndex
            console.log('prune ' + pruneHistoryIndex)

            xhr.send(JSON.stringify(formData));


        }
    }

    return handleInput
}


function setupResetSettingsButton() {
    const link = document.getElementById('reset-settings') as HTMLElement;
    if (!link) {
        return;
    }
    link.addEventListener('click', (e) => {
        e.preventDefault();
        fetch('/settings/default').then(r => r.json()).then(data => {
            // Select the form
            let form = document.getElementById('settings-form')! as HTMLFormElement;
            // Iterate over the keys in the JSON object
            for (let key in data) {
                if (data.hasOwnProperty(key)) {
                    // Find the form element that matches the key
                    // @ts-ignore
                    let input = form.elements[key];
                    if (input) {
                        // Update the value of the form element
                        input.value = data[key];
                    }
                }
            }
        })
    })
}


function updateScrollButton() {
    const div = document.getElementById('chat')! as HTMLDivElement;
    const scrollButton = document.getElementById('scrolldown-button')! as HTMLButtonElement;
    if ((div.offsetHeight + div.scrollTop) >= div.scrollHeight) {
        // The div is scrolled to the bottom, so hide the button
        scrollButton.style.display = 'none';
    } else {
        // The div is not scrolled to the bottom, so show the button
        scrollButton.style.display = 'block';
    }
}

function setupScrollButton() {
    const div = document.getElementById('chat')! as HTMLDivElement;
    const scrollButton = document.getElementById('scrolldown-button')! as HTMLButtonElement;

    scrollButton.addEventListener('click', () => {
        div.scrollTop = div.scrollHeight; // Scroll to bottom
    });

    // Call the function initially and whenever the user scrolls within the div
    updateScrollButton();
    div.addEventListener('scroll', updateScrollButton);
}

const run = () => {

        setupResetSettingsButton();
        setupScrollButton();

        setupUploadButton()

        const textInput = document.getElementById('input-box')! as HTMLDivElement;
        if (textInput) {
            textInput.addEventListener('keypress', getInputHandler(textInput))
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
