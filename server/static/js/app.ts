import hljs from "highlight.js";
import io from 'socket.io-client';
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
// Votint actions
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


    const messageExtra = document.createElement('div')
    messageExtra.className = 'message-header'
    messageDiv.appendChild(messageExtra);
    messageExtra.innerText = direction === 'me' ? 'You' : 'Assistant';

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
    }
    // else {
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
    // }
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
        age: string
    };
    type HistoryItems = HistoryItem[];
    const historyDiv = document.getElementById('history') as HTMLUListElement;
    historyDiv.innerHTML = "";
    const setHistory = (items: HistoryItems) => {
        let lastAge = '';
        items.forEach(item => {

            if (lastAge !== item.age) {
                const age = document.createElement('li');
                age.innerText = item.age;
                age.className = 'history-age-title';
                historyDiv.appendChild(age);
            }
            lastAge = item.age;

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
                renderHistoryMessages(item);
                scrollToBottom();
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

            // if (direction === 'them') {
            highlightCode(inner);  // highlight both directions
            // }
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
        mdString = mdString.replace(inlineCodeRegex, (match, code) => {
            return `<code class="inline">${escapeHTML(code)}</code>`;
        });
        // highlight inline **Title**
        // const inlineMarkdownRegex = /\*\*([^*]*)\*\*/g;

        // mdString = mdString.replace(inlineMarkdownRegex, (match, code) => {
        //     return `<code class="inline">${escapeHTML(code)}</code>`;
        // });

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

function setClipboardHandler() {
    document.addEventListener('click', (event) => {
        const target = event.target as HTMLElement;

        // Check if the clicked element is a copy button inside a .code-header
        if (target.matches('.code-header > .copy')) {
            event.preventDefault();

            // Find the associated code text to be copied
            const codeText = (target.parentElement!.nextElementSibling! as HTMLElement).innerText;

            // Copy the text to clipboard
            navigator.clipboard.writeText(codeText).then(() => {
                target.innerText = 'Copied';
                target.style.cursor = 'auto';

                setTimeout(() => {
                    target.innerText = 'Copy';
                    target.style.cursor = 'pointer';
                }, 3000);
            });
        }
    });
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
                const ident = renderMessage(inputElement.innerText, 'me', chat);

                const elem = document.getElementById(ident)!;
                const inner = elem.querySelector('.inner-message')! as HTMLElement;
                highlightCode(inner);

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
                    let jsonMessage;
                    try {
                        jsonMessage = JSON.parse(message);
                    } catch (e) {
                        console.log(e)
                    }

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

function setupMenu() {

    const menuLink = document.getElementById('menuLink')!;
    const textNode = menuLink.firstChild! as HTMLElement;

    const menu = document.getElementById('menu')!;

    menuLink.addEventListener('click', function (event) {
        menu.classList.toggle('hidden');
        event.preventDefault();
    });

    window.addEventListener('click', function (event) {
        let target = event.target! as HTMLElement;
        if (!menu.contains(target) && target !== menuLink) {
            menu.classList.add('hidden');
        }
        // todo: close popup when out of reach
        // const targetElement = document.getElementById('element');
    });


    for (let elem of document.getElementsByClassName('mode-button')) {
        elem.addEventListener('click', (e) => {
            e.preventDefault()
            const target = e.target! as HTMLElement;
            menu.classList.toggle('hidden');
            if (target.id === 'mode-chat') {
                textNode.textContent = 'Chat';
                return
            }
            if (target.id === 'mode-stackexchange') {
                textNode.textContent = 'Stackexchange';
                return
            }

        })
    }
}

function setupAudio() {
    let recordButton = document.getElementById('record') as HTMLButtonElement;
    if (!recordButton) {
        console.log('No record button')
        return
    }

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        console.log('Media Devices API or getUserMedia is not supported in this browser.');
        // Handle the lack of support here
        recordButton.disabled = true;
        return
    }

    const socket = io('ws://localhost:5000');
    let mediaRecorder: MediaRecorder | undefined;
    let isRecording = false;

    recordButton.addEventListener('click', (e) => {
        if (recordButton.disabled) {
            e.preventDefault();
            return
        }

        recordButton!.classList.toggle('recording')
        if (!isRecording) {
            startRecording();
        } else {
            stopRecording();
        }
        isRecording = !isRecording;
    });


    const startRecording = () => {
        navigator.mediaDevices.getUserMedia({audio: true})
            .then(stream => {
                mediaRecorder = new MediaRecorder(stream);
                mediaRecorder.ondataavailable = function (e) {
                    if (e.data.size > 0) {
                        socket.emit('audio_stream', e.data);
                    }
                };
                mediaRecorder.start(5000);
            })
            .catch(error => {
                console.error('Error accessing the microphone', error);
            });
    };

    const stopRecording = () => {
        if (mediaRecorder) {
            mediaRecorder.stop();
        }
    };
}

function setupTextInput() {
    const textInput = document.getElementById('input-box')! as HTMLDivElement;
    if (textInput) {
        textInput.addEventListener('keypress', getInputHandler(textInput))
    }

    setFocusToInputField(textInput);
}


const setupEscapeButtonForPopups = () => {
    document.addEventListener('keydown', function (event) {
        // close popups on escape key
        if (event.key === 'Escape') {
            // Remove the hash from the URL to close the element opened via CSS anchors
            window.location.hash = '';
        }
    });
};


const main = () => {

    setupMenu(); // Menu on top left
    setupResetSettingsButton(); // Reset Settings
    setupScrollButton(); // Scroll Button
    setupUploadButton() //

    setupTextInput();

    loadHistory();

    setClipboardHandler();

    setupEscapeButtonForPopups();

    setupAudio()
};

main()
