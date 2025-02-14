import hljs from "highlight.js";
import 'highlight.js/styles/github-dark.css';
// import CodeMirror from 'codemirror';
// import * as CodeMirrorNS from 'codemirror';
// const CodeMirror = (CodeMirrorNS as any).default || CodeMirrorNS;
import {javascript} from '@codemirror/lang-javascript'
import {python} from '@codemirror/lang-python'
import {cpp} from '@codemirror/lang-cpp'
import {rust} from '@codemirror/lang-rust'

import {
    crosshairCursor,
    drawSelection,
    dropCursor,
    highlightActiveLine,
    highlightActiveLineGutter,
    highlightSpecialChars,
    keymap,
    lineNumbers,
    rectangularSelection
} from '@codemirror/view'
import {
    bracketMatching,
    defaultHighlightStyle,
    foldGutter,
    foldKeymap,
    indentOnInput,
    indentUnit,
    syntaxHighlighting
} from '@codemirror/language'
import {basicSetup, EditorView} from 'codemirror'
import {EditorState, Compartment} from '@codemirror/state'
import {autocompletion, closeBrackets, closeBracketsKeymap, completionKeymap} from '@codemirror/autocomplete'
import {highlightSelectionMatches, searchKeymap} from '@codemirror/search'
import {defaultKeymap, history, historyKeymap} from '@codemirror/commands'
import {lintKeymap} from '@codemirror/lint'
// import 'codemirror/lib/codemirror.css';
// import 'codemirror/mode/javascript/javascript';

// import 'codemirror/lib/codemirror.css';
// import 'codemirror/mode/javascript/javascript';

let editor: EditorView = null;
let canvasEnabled = true;

const scrollToBottom = () => {
    let messages = document.getElementById("chat")!
    messages.scrollTo(0, messages.scrollHeight);
}

const getFormDataAsJSON = (formId: string): Record<string, string | number | boolean> => {
    const form = document.getElementById(formId) as HTMLFormElement;
    const formData: Record<string, string | number | boolean> = {};

    if (form) {
        // @ts-ignore
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
// Voting actions
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

const renderMessage = (message: string, direction: 'me' | 'them', chat: HTMLElement, innerMessageExtraClass?: string, renderButtons: boolean = true): string => {
    const ident = (Math.random() + 1).toString(36).substring(2);
    // let thought = "";
    const messageDiv = document.createElement('div');
    messageDiv.className = `message from-${direction}`;
    messageDiv.id = ident;

    const messageExtra = document.createElement('div')
    messageExtra.className = 'message-header'
    messageDiv.appendChild(messageExtra);
    messageExtra.innerText = direction === 'me' ? 'You' : 'Assistant';

    const innerMessageDiv = document.createElement('div');
    innerMessageDiv.className = 'inner-message';
    if (innerMessageExtraClass) {
        innerMessageDiv.classList.add(innerMessageExtraClass)
    }

    // if we have a <think></think> remove it
    const regex = /<think>([\s\S]*?)<\/think>([\s\S]*)/;
    const match = message.match(regex);
    if (match) {
        // thought = match[1]
        message = match[2];
    }
    innerMessageDiv.innerText = message.trim();

    messageDiv.appendChild(innerMessageDiv);
    if (renderButtons) {
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
    const uploadButton = document.getElementById('upload-button') as HTMLButtonElement;
    if (uploadButton) {
        uploadButton.addEventListener('click', (e) => {
            e.preventDefault();

            const existingErrorMessage = document.querySelector('[data-error-message]') as HTMLElement;
            if (existingErrorMessage) {
                if (existingErrorMessage.dataset.errorMessage) {
                    delete existingErrorMessage.dataset.errorMessage
                }
            }


            const formElement = document.getElementById("upload-form") as HTMLFormElement;
            const fileInput = formElement.querySelector('#file')! as HTMLInputElement;
            const parentDiv = fileInput.parentElement!;
            const help = parentDiv.nextElementSibling! as HTMLElement;

            // Create a new FormData object
            const formData = new FormData(formElement);
            const chat = document.getElementById('chat')!;
            uploadButton.disabled = true;
            fetch("/upload",
                {
                    body: formData,
                    method: "post"
                }).then((response) => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            }).then((jsonData) => {
                // Process the JSON data here
                console.log(jsonData);
                help.classList.remove('warning')
                if (jsonData.error) {
                    help.dataset.errorMessage = jsonData['error']
                    help.classList.add('warning')
                } else { // all set
                    document.location.hash = ''
                    renderMessage((formData.get('file') as any).name, "me", chat, 'file-icon', false);

                    if (jsonData['collection-visibility']) {
                        const menuLink = document.getElementById('menuLink');
                        if (menuLink) {
                            const textNode = menuLink.firstChild! as HTMLElement;
                            textNode.textContent = jsonData['collection-name'];
                            const collectionType = jsonData['collection-visibility'] === 'public' ? 'common' : 'user'
                            const subMenu = document.getElementById(`menu-collection-${collectionType}`)
                            if (subMenu) {
                                const button = document.createElement('a')
                                button.className = 'mode-button'
                                button.href = '#';
                                button.textContent = jsonData['collection-name'];
                                button.id = jsonData['collection-name'];
                                subMenu.appendChild(button);
                                // Get the current URL
                                const url = new URL(window.location.href);
                                // Update the search parameter
                                url.searchParams.set('collection', jsonData['collection-hashed-name']);
                                // Change the location object without reloading the page
                                history.replaceState({}, '', url);
                            }
                        }
                    }

                }
            })
                .catch((_error) => {
                    // Handle errors or display a message to the user
                    help.classList.add('warning', 'warning-file-upload-failed')
                })
                .finally(() => {
                    uploadButton.disabled = false;
                });
        })
    }

    const collectionSelector = document.getElementById('collection-selector') as HTMLSelectElement;
    const collectionName = document.getElementById('collection-name') as HTMLInputElement;
    const collectionVisibility = document.getElementById('collection-visibility') as HTMLInputElement;

    if (collectionSelector && collectionName && collectionVisibility) {
        const outerName = collectionName.closest('.block')!;
        const outerVisibility = collectionVisibility.closest('.block')!;
        const eventHandler = (event?: Event) => {
            if (event) {
                event.preventDefault();
            }
            if (collectionSelector.value === "New") {
                outerName.className = 'd-block';
                outerVisibility.className = 'd-block';
                collectionName.value = "";
                collectionVisibility.checked = false;
            } else {
                outerName.className = 'd-none'
                outerVisibility.className = 'd-none'
            }
        }
        collectionSelector.addEventListener('change', eventHandler)
        eventHandler();  // set it for starter
    }


};


const highlightCode = (inner: HTMLElement) => {

    const convertMarkdownToHTML = (mdString: string) => {
        // Replace triple backtick code blocks
        const codeBlockRegex = /```([a-z]*)\n([\s\S]*?)```/g;
        mdString = mdString.replace(codeBlockRegex, (_match, lang, code) => {
            const language = lang || 'bash';
            return `<div class="code-header"><div class="language">${language}</div><div class="copy">Copy</div></div><pre><code class="language-${language}">${escapeHTML(code)}</code></pre>`;
        });

        // Replace inline code
        const inlineCodeRegex = /`([^`]+)`/g;
        mdString = mdString.replace(inlineCodeRegex, (_match, code) => {
            return `<code class="inline">${escapeHTML(code)}</code>`;
        });
        // highlight inline **Title**
        // const inlineMarkdownRegex = /\*\*([^*]*)\*\*/g;

        // mdString = mdString.replace(inlineMarkdownRegex, (match, code) => {
        //     return `<code class="inline">${escapeHTML(code)}</code>`;
        // });

        return mdString;
    };

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
};

const loadHistory = () => {
    type Metadata = {
        file: string
    }
    type Message = {
        collection: string;
        metadata: Array<Metadata>;
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
            let innerMessageExtraClass: string | undefined = undefined;
            let renderButtons: boolean = true;
            if (msg.metadata) {
                innerMessageExtraClass = "file-icon";
                const fileSet = new Set(msg.metadata.map(item => item.file));
                msg.content = Array.from(fileSet).join(', ')
                // msg.content = msg.metadata.filename;
                renderButtons = false;
            }
            if (msg.collection) {
                const url = new URL(window.location.href);
                // Update the search parameter
                url.searchParams.set('collection', msg.collection);
                // Change the location object without reloading the page
                history.replaceState({}, '', url);
                const menuLink = document.getElementById('menuLink')!;
                const textNode = menuLink.firstChild! as HTMLElement;

                const collectionLink = document.querySelector(`a[id="${msg.collection}"]`)
                if (collectionLink) {
                    textNode.textContent = collectionLink.textContent;
                } else {
                    console.log('Problems setting the collection name')
                }
            }

            const ident = renderMessage(msg.content, direction, chat, innerMessageExtraClass, renderButtons);

            const msgDiv = document.getElementById(ident);
            const inner = msgDiv!.getElementsByClassName('inner-message')[0] as HTMLElement;

            highlightCode(inner);  // highlight both directions
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


const setClipboardHandler = () => {
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
};


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

    function getAllChunks(responseText: string) {
        const trimmed = responseText.trim();
        if (!trimmed.includes('}{')) {
            try {
                return [JSON.parse(trimmed)];
            } catch (e) {
                return [];
            }
        }
        const parts = trimmed.split('}{');
        for (let i = 0; i < parts.length; i++) {
            if (i > 0) parts[i] = '{' + parts[i];
            if (i < parts.length - 1) parts[i] = parts[i] + '}';
        }
        const allResponses = [];
        for (const part of parts) {
            try {
                allResponses.push(JSON.parse(part));
            } catch (e) {
                // ignore any invalid/incomplete parts
            }
        }
        return allResponses;
    }

    function handleInput(e: KeyboardEvent) {
        if (e.key === 'Enter' && e.shiftKey === false) {
            e.preventDefault();
            const xhr = new XMLHttpRequest();
            let m = inputElement.innerText;
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
                    inputElement.contentEditable = "true";
                })
            }

            stopButton.disabled = false;

            const ident = renderMessage('', 'them', chat)
            const elem = document.getElementById(ident)!;
            let inner = elem.querySelector('.inner-message')! as HTMLElement;
            let textField = inner;
            inner.innerHTML = '<div class="loading"></div>'

            scrollToBottom()

            xhr.open('POST', '/');
            let index = 0;

// Current mode (which element to append to)
            let mode = "normal"; // can be: "normal", "think", "codecanvas"

// Rolling buffer to detect multi-token markers like < code canvas >
            let rollingBuffer: string[] = [];

// A queue for tokens to display with a delay: each item => { element, token }
            let flushQueue: Record<string, string>[] = [];

// Are we currently showing tokens from flushQueue?
            let isFlushing = false;

            let newCode = ""
            let lineNumber = 1;
            let existingCode = editor.state.doc.toString()

//------------------------------------------------------------------
// processToken(token): returns an array of { element, token } objects
// telling us which element to append to, and what text to append.
//------------------------------------------------------------------
            function processToken(token: string) {
                const flushList: Array<Record<string, string>> = [];

                function pushToFlushList(t: string) {
                    let element;
                    switch (mode) {
                        case "think":
                            element = 'think';
                            break;
                        case "codecanvas":
                            element = 'codecanvas';
                            break;
                        default:
                            textField = inner
                            element = 'text';
                    }
                    flushList.push({element, token: t});
                }

                // Helper that checks if the tail of rollingBuffer forms joinedString ignoring whitespace.
                function endsWithJoined(joinedString: string) {
                    let combined = "";
                    for (let i = rollingBuffer.length - 1; i >= 0; i--) {
                        const t = rollingBuffer[i].replace(/\s+/g, "");
                        combined = t + combined;
                        // If we fully matched the marker
                        if (combined === joinedString) {
                            let neededTokens = 0;
                            let temp = "";
                            for (let j = rollingBuffer.length - 1; j >= 0; j--) {
                                const seg = rollingBuffer[j].replace(/\s+/g, "");
                                temp = seg + temp;
                                neededTokens++;
                                if (temp === joinedString) {
                                    rollingBuffer.splice(rollingBuffer.length - neededTokens, neededTokens);
                                    return true;
                                }
                            }
                        }
                        // If partial combination no longer matches as suffix, break
                        if (!joinedString.endsWith(combined)) {
                            return false;
                        }
                    }
                    return false;
                }

                // If currently in 'think' mode, only watch for '</think>' to return to normal.
                if (mode === "think") {
                    // If single token = '</think>', switch mode, do not flush marker.
                    if (token === "</think>") {
                        mode = "normal";
                        return flushList; // no output for the marker
                    }
                    // Otherwise, push token and see if we form '</think>' ignoring whitespace.
                    rollingBuffer.push(token);

                    if (endsWithJoined("</think>")) {
                        mode = "normal";
                        return flushList;
                    }

                    // If we didn't detect '</think>', flush everything to the thinkElement
                    // (We know these tokens won't form another marker, so we can just flush now)
                    while (rollingBuffer.length > 0) {
                        pushToFlushList(rollingBuffer.shift());
                    }
                    return flushList;
                }

                // If currently in 'codecanvas' mode, only watch for '</codecanvas>' to return to normal.
                if (mode === "codecanvas") {
                    // If single token = '</codecanvas>', switch mode, do not flush marker.
                    if (token === "</codecanvas>") {
                        mode = "normal";
                        return flushList;
                    }
                    // Otherwise, accumulate token and check for multi-token marker
                    rollingBuffer.push(token);

                    if (endsWithJoined("</codecanvas>")) {
                        // if we matched it in rollingBuffer, remove it and switch mode.
                        mode = "normal";
                        return flushList;
                    }

                    // If we haven't found '</codecanvas>', flush everything that can't be part of a marker.
                    function couldStartMarker(t) {
                        // We'll skip flushing tokens that have '<' if we suspect they're part of the marker.
                        return t.includes('<');
                    }

                    while (rollingBuffer.length > 0) {
                        if (couldStartMarker(rollingBuffer[0])) {
                            break;
                        }
                        pushToFlushList(rollingBuffer.shift());
                    }
                    return flushList;
                }

                // Otherwise, mode === "normal"; let's see if we open a think or codecanvas.

                // First, handle single-token markers if the model merges them.
                if (token === "<think>") {
                    mode = "think";
                    inner.innerHTML = "";
                    const details = document.createElement('details');
                    details.classList.add('think-details')

                    inner.appendChild(details);
                    const summary = document.createElement('summary');
                    summary.classList.add('think-title')
                    summary.classList.add('shimmer')
                    summary.innerText = 'Thinking';
                    details.appendChild(summary)
                    const p = document.createElement('div');
                    p.classList.add('think-content')

                    details.appendChild(p)
                    inner.appendChild(details)

                    // textField = p;
                    const after = document.createElement('div');
                    // after.classList.add('loading')
                    inner.append(after);
                    after.innerHTML = '<div class="loading"></div>'
                    inner = after;
                    textField = p;
                    return flushList;
                }
                if (token === "<codecanvas>") {
                    mode = "codecanvas";
                    return flushList;
                }

                // push the token into rollingBuffer and check for <think> or <codecanvas>
                rollingBuffer.push(token);

                if (endsWithJoined("<think>")) {
                    mode = "think";
                    return flushList;
                }
                if (endsWithJoined("<codecanvas>")) {
                    mode = "codecanvas";
                    return flushList;
                }

                // If we haven't found a marker, flush everything from the front that cannot be a marker start.
                function couldStartMarker(t) {
                    return t.includes("<");
                }

                while (rollingBuffer.length > 0) {
                    if (couldStartMarker(rollingBuffer[0])) {
                        break;
                    }
                    pushToFlushList(rollingBuffer.shift());
                }

                return flushList;
            }

//------------------------------------------------------------------
// onStreamProgress(jsonChunk):
//   - Extract the token
//   - process it (state machine, rolling buffer)
//   - add the resulting flushList to the global flushQueue
//   - schedule flush if not already in progress
//------------------------------------------------------------------
            function onStreamProgress(jsonChunk: any) {
                const token = jsonChunk.choices[0].delta.content;
                const flushList = processToken(token);
                flushList.forEach(item => flushQueue.push(item));
                scheduleFlush();
            }

//------------------------------------------------------------------
// scheduleFlush():
//   - If not already flushing, start the delayed chain
//------------------------------------------------------------------
            function scheduleFlush() {
                if (!isFlushing) {
                    isFlushing = true;
                    flushNext();
                }
            }

            //------------------------------------------------------------------
            // flushNext():
            //   - Pops one token from flushQueue
            //   - Appends it to the correct element
            //   - Repeats after some interval
            //------------------------------------------------------------------
            function flushNext() {
                if (flushQueue.length === 0) {
                    isFlushing = false;
                    return;
                }

                const {element, token} = flushQueue.shift() as Record<string, string>;
                if (element === 'text') {
                    textField.textContent += token;
                } else if (element === 'think') {
                    textField.textContent += token;
                } else if (element === 'codecanvas') {

                    if (token.endsWith('\n')) {
                        // editor.state.doc.append(token)
                        let pos = editor.state.doc.lineAt(lineNumber)

                        editor.dispatch({changes: {
                          from: pos.from,
                          to: pos.to,
                          insert: token
                        }})
                        lineNumber ++;
                    } else {
                        newCode += token;
                    }


                } else {
                    console.log('Do not know where to place ' + element + " with token " + token)
                }
                // element.value += token;
                if (element)
                    flushNext();
            }

// The rest of your XHR logic:
            xhr.onprogress = function () {
                const chunks = getAllChunks(xhr.responseText);

                while (index < chunks.length) {
                    const chunk = chunks[index];
                    if (chunk) {
                        if (chunk.choices[0].finish_reason === 'stop') {
                            const timings = chunk.timings;
                            let model = chunk.model;
                            if (model) {
                                model = model.split('/').slice(-1);
                            }

                            if (timings) {
                                const timing = document.getElementById('timing-info') as HTMLElement;
                                timing.innerText = `${model}: ${round(1000.0 / timings.predicted_per_token_ms, 1)} t/s `;
                            }

                            highlightCode(textField);
                            inputElement.contentEditable = "true";
                            stopButton.disabled = true;
                            loadHistory();
                            inputElement.focus();
                            for (const elem1 of document.getElementsByClassName('shimmer')) {
                                elem1.classList.remove('shimmer');
                            }
                        } else {
                            onStreamProgress(chunk);
                        }
                    }
                    updateScrollButton();
                    index++;
                }
            };


            xhr.addEventListener("error", function (e) {
                console.log("error: " + e);
            });

            xhr.onload = function () {

                // if (isMainInput) {
                //     inputElement.contentEditable = "true";
                // }
                // setFocusToInputField(mainInput);
                // stopButton.disabled = true;
                // loadHistory()
            }
            xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");

            const formData = getFormDataAsJSON('settings-form')

            //
            const content = editor.state.doc.toString().trim();
            if (content && canvasEnabled) {
                m += '\n';
                m += "<codecanvas>>";
                m += content;
                m += "</codecanvas>>"
                console.log("we have a canvas")
            } else {
                console.log("no canvas")
            }

            formData.input = m
            formData.pruneHistoryIndex = pruneHistoryIndex

            //
            // editor.dispatch({changes: {
            //   from: 0,
            //   to: editor.state.doc.length,
            //   insert: ""
            // }})

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

    const menuLink = document.getElementById('menuLink');
    if (!menuLink) {
        return;
    }
    const textNode = menuLink.firstChild! as HTMLElement;

    const menu = document.getElementById('menu')!;

    const key = 'collection'

    // Get the current location and parse it into a URL object
    const curUrl = new URL(window.location.href);

    menuLink.addEventListener('click', function (event) {
        menu.classList.toggle('hidden');
        event.preventDefault();
    });

    // hide menu
    window.addEventListener('click', function (event) {
        let target = event.target! as HTMLElement;
        if (!menu.contains(target) && target !== menuLink) {
            menu.classList.add('hidden');
        }
    });


    // get and set current mode
    const selectedMode = curUrl.searchParams.get(key);
    for (let elem of document.getElementsByClassName('mode-button')) {
        // @ts-ignore
        elem.addEventListener('click', (e: MouseEvent) => {
            e.preventDefault()
            const target = e.target! as HTMLElement;
            menu.classList.toggle('hidden');

            const updateUrlParam = (term: string) => {
                // Add or update the 'q' parameter in the query string
                if (!curUrl.searchParams.has(key)) {
                    curUrl.searchParams.append(key, term); // Append a new search param if it doesn't exist
                } else {
                    curUrl.searchParams.set(key, term); // Overwrite the existing search param with the new value
                }
                // Update the URL in the browser
                window.history.pushState({}, '', curUrl.href);
            }

            if (target.id === 'mode-chat') {
                textNode.textContent = 'Chat';
                updateUrlParam('')
                return
            }
            // if (target.id === 'mode-stackexchange') {
            // const vals = target.id.split('-')
            // console.log(vals)


            textNode.textContent = target.textContent;
            updateUrlParam(target.id)
            // return
            // }

        })
        //update current selection
        if (selectedMode && elem.id === selectedMode) {
            // console.log('sekect ', elem)
            (elem as HTMLAnchorElement).click();
            menu.classList.add('hidden');
        }
    }
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


const setupSettingsMustBeSet = () => {
    let form = document.getElementById('settings-form');
    if (!form) {
        return
    }
    const inputs = form.querySelectorAll('input[required]')

    const validateInput = () => {

        inputs.forEach(elem => {
            const input = elem as HTMLInputElement;
            const parent = input.parentElement as HTMLDivElement;
            const help = parent.nextElementSibling as HTMLDivElement;

            if (input.value.trim() === '') {
                help.classList.add('warning');
            } else {
                help.classList.remove('warning');
            }
        });
    };

    inputs.forEach(input => {
        input.addEventListener('input', validateInput);
    });
    validateInput();
};

const setupCollectionDeletion = () => {
    window.addEventListener('click', function (event) {
        let target = event.target! as HTMLElement;
        if (target.classList.contains('delete-collection-item')) {
            event.preventDefault()
            const collectionToDelete = target.previousElementSibling!.id;
            const url = `/delete/collection/${collectionToDelete}`;
            fetch(url).then(() => {
                document.location.pathname = '/';  // new session
            })
        }
    });
};

const main = () => {


    setupResetSettingsButton(); // Reset Settings
    setupScrollButton(); // Scroll Button
    setupUploadButton() //

    setupTextInput();

    loadHistory();

    setClipboardHandler();

    setupEscapeButtonForPopups();

    setupSettingsMustBeSet();

    setupMenu(); // Menu on top left

    setupCollectionDeletion();
    const initialText = ''
    const targetElement = document.querySelector('#editor')!
    let language = new Compartment, tabSize = new Compartment

    editor = new EditorView({
        doc: initialText,

        extensions: [
            basicSetup,
            lineNumbers(),
            highlightActiveLineGutter(),
            highlightSpecialChars(),
            // history(),
            foldGutter(),
            drawSelection(),
            dropCursor(),
            EditorState.allowMultipleSelections.of(true),
            indentOnInput(),
            indentUnit.of("    "),
            syntaxHighlighting(defaultHighlightStyle, {fallback: true}),
            bracketMatching(),
            closeBrackets(),
            autocompletion(),
            rectangularSelection(),
            crosshairCursor(),
            highlightActiveLine(),
            highlightSelectionMatches(),
            keymap.of([
                ...closeBracketsKeymap,
                ...defaultKeymap,
                ...searchKeymap,
                ...historyKeymap,
                ...foldKeymap,
                ...completionKeymap,
                ...lintKeymap,
            ]),
            // javascript(),
            // python(),
            language.of(python()),

        ],
        parent: targetElement,
    })

    editor.dom.addEventListener('input', debounce(detectAndSetMode, 500));

    function detectAndSetMode() {
        const content = editor.state.doc.toString();

        const result = hljs.highlightAuto(content, ["python", "cpp", "javascript", "rust"]);
        console.log(result)
        // let newMode = 'javascript';
        if (result.language === 'python') {
            language.reconfigure(python())
        } else if (result.language === 'cpp') {
            language.reconfigure(cpp())
        } else if (result.language === 'javascript') {
            language.reconfigure(javascript())
        } else if (result.language === 'rust') {
            language.reconfigure(rust())
        }

        // editor.state.('mode', newMode);
    }


    // editor.on('change', debounce(detectAndSetMode, 1000));

//
//
//     const toggleSidebarBtn = document.getElementById('toggle-sidebar');
// const sidebar = document.getElementById('sidebar');
// const container = document.getElementById('container');
//
// const toggleEditorBtn = document.getElementById('toggle-editor');
// const editorT = document.getElementById('editorT');
//
// // Toggle sidebar
// toggleSidebarBtn.addEventListener('click', () => {
//   // Toggle a class on sidebar to collapse it
//   sidebar.classList.toggle('collapsed');
//   // Also adjust container margin
//   container.classList.toggle('sidebar-collapsed');
// });
//
// // Toggle editor visibility
// toggleEditorBtn.addEventListener('click', () => {
//   // Simply hide/show editor by toggling a "hidden" class
//   editorT.classList.toggle('hidden');
// });
}

function debounce(fn: any, delay: number) {
    let timeout: number;
    return function (...args: any[]) {
        clearTimeout(timeout);
        timeout = window.setTimeout(() => fn.apply(this, args), delay);
    }
}


main();

