import hljs from "highlight.js";
import 'highlight.js/styles/github-dark.css';
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
import {Compartment, EditorState} from '@codemirror/state'
import {autocompletion, closeBrackets, closeBracketsKeymap, completionKeymap} from '@codemirror/autocomplete'
import {highlightSelectionMatches, searchKeymap} from '@codemirror/search'
import {defaultKeymap, historyKeymap} from '@codemirror/commands'
import {lintKeymap} from '@codemirror/lint'
// @ts-ignore
import katex from "katex";
// import {marked} from "marked";
import {marked} from "marked";

document.documentElement.style.setProperty("--katex-font", "serif");

const languageSubset = ["python", "cpp", "javascript", "rust", "java", "typescript", "bash", "csharp", "c"];

interface CodeBlock {
    lang: string
    raw: string
    text: string
    type: string
}


let editor: EditorView | null = null;
let canvasEnabled = true;

// just scroll to the bottom of the chat window
const scrollToBottom = () => {
    let messages = document.getElementById("chat")!
    messages.scrollTo(0, messages.scrollHeight);
}

// extract settings parameters from settings form as JSON
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

// Simple rounding function (for tokens/s)
const round = (originalNumber: number, digits: number) => {
    const t = 10 ** digits;
    return Math.round(originalNumber * t) / t;
}

// Allow editing a former from-me message
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


/**
  * Code renderer for Marked (Markdown, code, latex):
  * 1) Does *only* placeholders for LaTeX (inline/block) so Marked never sees the raw LaTeX.
  * 2) Then uses Marked for normal Markdown (including code blocks),
  * 3) Re-injects KaTeX for placeholders at the end,
  * 4) Avoids any math extension in Marked.
  * 5) Also, ensures highlight.js sees only code strings.
  * Make sure you remove or disable any other math extension or plugin that might parse LaTeX.
  */
const blockCodeRenderer: any = {
    code(code: CodeBlock, infostring: string) {
        let lang = infostring?.trim() || ''
        let highlighted: string;
        if (lang && hljs.getLanguage(lang)) {
            console.log("Have a look at this")
            // @ts-ignore
            highlighted = hljs.highlight(code, {language: lang}).value
        } else {
            // fallback auto-detection
            // const autoResult = hljs.highlightAuto(escapeHtml(code.text), languageSubset) //escapeHTML?
            const autoResult = hljs.highlightAuto(code.text, languageSubset) //escapeHTML?
            // const escaped = escapeHtml(autoResult.value)
            highlighted = autoResult.value
            lang = autoResult.language || ''
        }
        return `\n<div class="code-header">\n  <div class="language">${lang}</div>\n  <div class="copy" onclick="">Copy</div>\n</div><pre><code class="hljs language-${lang}">${highlighted}</code></pre>`
    }
}


// Strips the outer LaTeX delimiters from a match so KaTeX sees only the contents.
const stripMathDelimiters = (latex: string): string => {
    // block $$...$$
    if (/^\${2}[\s\S]*?\${2}$/.test(latex)) {
        return latex.slice(2, -2).trim()
    }
    // block \[...\]
    // noinspection RegExpRedundantEscape
    if (/^\\\[[\s\S]*?\\\]$/.test(latex)) {
        return latex.slice(2, -2).trim()
    }
    // inline \(...\)
    if (/^\\\([\s\S]*?\\\)$/.test(latex)) {
        return latex.slice(2, -2).trim()
    }
    // inline $...$
    if (/^\$[\s\S]*?\$$/.test(latex)) {
        return latex.slice(1, -1).trim()
    }
    return latex
};


// parses a message and renders cocde, markdown and latex
const parseMessage = (text: string): string => {
    // 1) Regex to find *all* LaTeX forms: block or inline
    //    $$...$$, \[...\], \(...\), $...$
    // We do placeholders so Marked never sees actual LaTeX., same for codecanvas

    // function preprocessMessage(text: string): { processed: string, placeholders: Map<string, string> } {
    function preprocessMessage(text: string): { processed: string, placeholders: Map<string, string> } {
        const placeholders = new Map();
        let counter = 0;

        const processed = text.replace(/<codecanvas>[\s\S]*?<\/codecanvas>/g, match => {
            const placeholder = `@@CODECANVAS_${counter}@@`;
            placeholders.set(placeholder, match);
            counter++;
            return placeholder;
        });

        return { processed, placeholders };
    }

    function postprocessMessage(parsedText: string, placeholders: Map<string, string>): string {
        let result = parsedText;
        placeholders.forEach((original, placeholder) => {
            result = result.replace(placeholder, original);
        });
        return result;
    }
    // noinspection RegExpRedundantEscape
    const mathRegex = /(\${2}[\s\S]*?\${2}|\\\[[\s\S]*?\\\]|\\\([\s\S]*?\\\)|\$[\s\S]*?\$)/g

    const rawMath: string[] = []
    let match: RegExpExecArray | null
    while ((match = mathRegex.exec(text)) !== null) {
        rawMath.push(match[0])
    }

    // 2) Replace each math snippet with a unique placeholder
    let placeholderText = text
    rawMath.forEach((m, i) => {
        const placeholder = `@@MATH_${i}@@`
        placeholderText = placeholderText.replace(m, placeholder)
    })



    // 3) Parse placeholderText with Marked for normal markdown
    // marked.setOptions({mangle: false, smartypants: false})
    marked.use({renderer: blockCodeRenderer})

    // Ensure no math extension is used. The below is all we do.
    // 4) Re-inject KaTeX for each placeholder
    const { processed, placeholders } = preprocessMessage(placeholderText)
    let finalHtml = marked.parse(processed) as string
    finalHtml = postprocessMessage(finalHtml, placeholders);

    // finalHtml = postprocessMessage(finalHtml, placeholders)
    // finalHtml.replaceAll('<ins>', '<codecanvas>')
    // finalHtml.replaceAll('</ins>', '</codecanvas>')
    rawMath.forEach((latex, i) => {
        const placeholder = `@@MATH_${i}@@`
        // Decide block vs. inline
        // noinspection RegExpRedundantEscape
        const isBlock = (
            /^\${2}[\s\S]*?\${2}$/.test(latex) ||
            /^\\\[[\s\S]*?\\\]$/.test(latex)
        )
        // Strip the delimiters
        const stripped = stripMathDelimiters(latex)
        let rendered = "";
        // Render KaTeX
        try {
            rendered = katex.renderToString(stripped, {
                throwOnError: true,
                displayMode: isBlock
            })
        } catch (e) {
            console.log(stripped, latex)
        }
        // Replace the placeholder
        finalHtml = finalHtml.replace(placeholder, rendered)
    })

    return finalHtml
};

// creates a new from-me or from-them message and inserts the necessary html
const renderMessage = (message: string, direction: 'me' | 'them', chat: HTMLElement, innerMessageExtraClass?: string, renderButtons: boolean = true): string => {
    const ident = (Math.random() + 1).toString(36).substring(2);
    // let thought = "";
    const messageDiv = document.createElement('div');
    messageDiv.className = `message from-${direction}`;
    messageDiv.id = ident;

    const messageExtra = document.createElement('div')
    messageExtra.className = 'message-header'
    messageDiv.appendChild(messageExtra);
    messageExtra.innerText = direction === 'me' ? 'Me' : 'Assistant';

    const innerMessageDiv = document.createElement('div');
    innerMessageDiv.className = 'inner-message';
    if (innerMessageExtraClass) {
        innerMessageDiv.classList.add(innerMessageExtraClass)
    }

    // if we have a <think></think> remove it, note: This is also done on server side. Here it would
    // just hide the think block. If we remove it on the server it will be removed from the context
    const regex = /<think>([\s\S]*?)<\/think>([\s\S]*)/;
    const match = message.match(regex);
    if (match) {
        // thought = match[1]
        message = match[2];
    }
    // innerMessageDiv.innerHtml = message.trim();

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
        else {
            // todo: Branch
            // todo: Regenerate
            // todo sidebar button oike in chatgpt?
            // const themButtonDiv = document.createElement('div');
            // themButtonDiv.className = 'edit-button';
            // const branchLink = document.createElement('a');
            // branchLink.href = '/branch/';
            // branchLink.id = `branch-${ident}`;
            // branchLink.title = 'Branch conversation'
            // branchLink.classList.add('branch-button')
            //
            //
            // const icon = document.createElement('i')
            // icon.classList.add('gg-git-pull')
            // branchLink.appendChild(icon)
            // const text = document.createElement("span")
            // branchLink.appendChild(text)
            // text.textContent = 'Branch'
            //
            //
            // // branchLink.textContent = '➞';
            // themButtonDiv.appendChild(branchLink);
            // console.log('adding branch')
            //
        //
        // const downvoteLink = document.createElement('a');
        // downvoteLink.href = '/downvote/';
        // downvoteLink.id = `downvote-${ident}`;
        // downvoteLink.textContent = '➞';
        // voteButtonDiv.appendChild(downvoteLink);
        //
        //     messageDiv.appendChild(themButtonDiv);
        //
        // upvoteLink.addEventListener('click', handleUpvoteAction);
        // downvoteLink.addEventListener('click', handleDownvoteAction);
        //
        //
        }
    }

    // renderMixedContent(message)
    innerMessageDiv.innerHTML = parseMessage(message);
    chat.appendChild(messageDiv);

    return ident;
};

//
const setFocusToInputField = (textInput: HTMLDivElement) => {
    if (textInput) {
        setTimeout(() => {
            textInput.focus()
        }, 200)
    }
};

// Setup the action for uploading a file
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

// Helper that checks if the tail of rollingBuffer forms joinedString ignoring whitespace.
function endsWithJoined(rollingBuffer: Array<string>, joinedString: string) {
    let combined = rollingBuffer.join("").replace(/\s+/g, "");  // strange the replace seems necessary
    return combined.endsWith(joinedString);
}

// replaces a line in the editor view
const replaceLine = (view: EditorView, lineNumber: number, newText: string) => {
    let state = view.state;
    let line: any;

    if (lineNumber > state.doc.lines) {  // end of document
        line = {from: state.doc.length, to: state.doc.length}
        newText = "\n" + newText;  // add the new line
    } else {
        line = state.doc.line(lineNumber);  // Get the line object
    }

    if (newText === line.text) {
        return
    }
    let transaction = state.update({
        changes: {from: line.from, to: line.to, insert: newText}
    });

    view.dispatch(transaction);
};

// load history and render it in the sidebar
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

            renderMessage(msg.content, direction, chat, innerMessageExtraClass, renderButtons);

            // const msgDiv = document.getElementById(ident);
            // const inner = msgDiv!.getElementsByClassName('inner-message')[0] as HTMLElement;

            const lastMatch = findLastCodeCanvasBlock(msg.content)
            if (editor && lastMatch) {
                // console.log(lastMatch)
                let transaction = editor.state.update({
                    changes: {from: 0, to: editor.state.doc.length, insert: lastMatch}
                });
                editor.dispatch(transaction);
                toggleRightPanel(true);
                toggleSidebar()
            }

            // highlightCode(inner);  // highlight both directions
        })
    }
    const index = document.location.pathname.indexOf('/c/')
    let url = '/history'
    if (index >= 0) {
        url += '/' + document.location.pathname.slice(index + 3)  // 3 is length of '/c/'
    }
    fetch(url).then((r) => r.json()).then(setHistory)
};

// this finds the last codecanvas block and renders it in the editor
const findLastCodeCanvasBlock = (text: string) => {
    let stack = [];
    let lastBlock = null;
    let startIndex = -1;
    let endIndex = -1;

    let regex = /<\/?codecanvas>/g;
    let match: any;

    while ((match = regex.exec(text)) !== null) {
        if (match[0] === "<codecanvas>") {
            stack.push(match.index);
        } else if (match[0] === "</codecanvas>" && stack.length > 0) {
            startIndex = stack.pop()!;
            endIndex = match.index + match[0].length;

            // Update lastBlock when a complete block is found
            lastBlock = text.substring(startIndex, endIndex);
        }
    }
    return lastBlock ? lastBlock.replace(/<\/?codecanvas>/g, "").trim() : null;
};

// if we edit a from-me message, we use this to remove all subsequent messages
const removeAllChildrenAfterIndex = (parentElement: HTMLElement, index: number) => {
    // Assuming `parentElement` is the DOM element and `index` is the given index
    while (parentElement.children.length > index + 1) {
        parentElement.removeChild(parentElement.lastChild!);
    }
};

// remove lines after a given line number in the edito view
const removeLinesAfter = (editor: EditorView, lineNumber: number) => {
    let state = editor.state;
    let line = state.doc.line(lineNumber);
    if (lineNumber >= state.doc.lines) return;

    let from = line.from;  // Start of the next line
    let to = state.doc.length; // End of the document

    editor.dispatch({
        changes: { from, to, insert: "" }
    });
};

// for copy code to clipboard action
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

// If we haven't found '</codecanvas>', flush everything that can't be part of a marker.
// const couldStartMarker = (t: string) => {
//     // We'll skip flushing tokens that have '<' if we suspect they're part of the marker.
//     return t.includes('<');
// };


const KNOWN_MARKERS = ["<codecanvas>", "</codecanvas>", "<think>", "</think>"];

function isPotentialMarker(bufferStr: Array<string>) {
    return KNOWN_MARKERS.some(marker => marker.startsWith(bufferStr.join("")));
}
// get all valid chunks from partial xhr responses
const getAllChunks = (input: string) => {
    let allResponses = [];
    let buffer: string;
    let candidate = "";

    for (let i = 0; i < input.length; i++) {
        candidate += input[i];
        try {
            const parsed = JSON.parse(candidate);

            // If we parsed successfully, store it
            allResponses.push(parsed);

            // Reset candidate
            candidate = "";
        } catch (e) {
            // If parsing fails, keep accumulating
            // do nothing, just continue
        }
    }

    // Whatever remains in candidate is incomplete JSON
    buffer = candidate;
    return {allResponses, buffer};
};


// handles a new message
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
            let m = inputElement.innerText;
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

            //------------------------------------------------------------------
            // processToken(token): returns an array of { element, token } objects
            // telling us which element to append to, and what text to append.
            //------------------------------------------------------------------


            // function processToken(token) {
            //   rollingBuffer.push(token);
            //   while (rollingBuffer.length > 0) {
            //     // Check if what we have so far is a full marker or partial prefix
            //     const { matchedMarker, couldStillBeMarker } = mightFormMarker(rollingBuffer);
            //     if (matchedMarker) {
            //       // The entire buffer matches e.g. "<codecanvas>"
            //       rollingBuffer = [];
            //       // handle switching mode to codecanvas, etc.
            //       mode = "codecanvas";
            //       return;
            //     } else if (couldStillBeMarker) {
            //       // The joined buffer is still a prefix (e.g. "<codec"),
            //       // so let's break and wait for more tokens
            //       break;
            //     } else {
            //       // We definitely do not match or prefix any known marker.
            //       // Flush the first token out of the buffer as normal text.
            //       pushToFlushList(rollingBuffer.shift());
            //     }
            //   }
            // }
            //
            //
            const processToken = (token: string) => {
                const flushList: Array<Record<string, string>> = [];

                // console.log("Token: " + token + "   Mode: " + mode)
                function pushToFlushList(t: string) {
                    let element: string;
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

                // If currently in 'think' mode, only watch for '</think>' to return to normal.
                if (mode === "think") {
                    // If single token = '</think>', switch mode, do not flush marker.
                    if (token === "</think>") {
                        mode = "normal";
                        return flushList; // no output for the marker
                    }
                    if (endsWithJoined(rollingBuffer, "</think>")) {
                        pushToFlushList("\n</think>\n")
                        mode = "normal";
                        rollingBuffer = [];
                        return flushList;
                    }
                    // Otherwise, push token and see if we form '</think>' ignoring whitespace.
                    rollingBuffer.push(token);

                    // If we didn't detect '</think>', flush everything to the thinkElement
                    // (We know these tokens won't form another marker, so we can just flush now)
                    while (rollingBuffer.length > 0) {
                        pushToFlushList(rollingBuffer.shift()!);
                    }
                    return flushList;
                }

                // If currently in 'codecanvas' mode, only watch for '</codecanvas>' to return to normal.
                if (mode === "codecanvas") {
                    // Otherwise, accumulate token and check for multi-token marker
                    rollingBuffer.push(token);

                    if (endsWithJoined(rollingBuffer, "</codecanvas>")) {
                        let lines = rollingBuffer.join("").split('\n')
                        for (const line of lines) {
                            if(line.trim() === '</codecanvas>') {
                                continue
                            }
                            pushToFlushList(line)
                            pushToFlushList('\n')
                        }

                        // if we matched it in rollingBuffer, remove it and switch mode.
                        mode = "normal";
                        pushToFlushList("\n</codecanvas>\n")
                        // reset the buffer
                        rollingBuffer = [];

                        // flushList.push({element: "codecanvas", token: "\n"});
                        return flushList;
                    }

                    while (rollingBuffer.length > 0) {
                        if (isPotentialMarker(rollingBuffer)) {
                            break;
                        }
                        pushToFlushList(rollingBuffer.shift()!);
                    }


                    return flushList;
                }

                if (token === null) {
                    token = "";
                }
                // First, handle single-token markers if the model merges them.
                if (token.startsWith("<think>")) {
                    // pushToFlushList("\n<think>\n")
                    pushToFlushList(token.slice("<think>".length))
                    token = "<think>"
                }
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

                // push the token into rollingBuffer and check for <think> or <codecanvas>
                rollingBuffer.push(token);

                if (endsWithJoined(rollingBuffer, "<codecanvas>")) {
                    pushToFlushList("\n<codecanvas>\n")
                    mode = "codecanvas";
                    rollingBuffer = [];
                    return flushList;
                }
                if (endsWithJoined(rollingBuffer, "<think>")) {
                    pushToFlushList("\n<think>\n")
                    mode = "think";
                    rollingBuffer = [];
                    return flushList;
                }

                while (rollingBuffer.length > 0) {
                    if (isPotentialMarker(rollingBuffer)) {
                        break;
                    }
                    pushToFlushList(rollingBuffer.shift()!);
                }

                return flushList;
            };
            //------------------------------------------------------------------
            // flushNext():
            //   - Pops one token from flushQueue
            //   - Appends it to the correct element
            //   - Repeats after some interval
            //------------------------------------------------------------------
            const flushNext = () => {
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
                    newCode += token;
                    if(newCode.replace(/\s+/g, "") == '</codecanvas>') {
                        newCode = "";  // dont output
                        // ignore this token

                    } else { // todo: This is ugly

                        if (token.endsWith('\n')) {
                            replaceLine(editor!, lineNumber, newCode.slice(0, -1))
                            lineNumber++;
                            newCode = "";  // reset
                        }
                    }
                } else {
                    console.warn('Do not know where to place ' + element + " with token " + token)
                }
                if (element)
                    flushNext();
            };
            //------------------------------------------------------------------
            // scheduleFlush():
            //   - If not already flushing, start the delayed chain
            //------------------------------------------------------------------
            const scheduleFlush = () => {
                if (!isFlushing) {
                    isFlushing = true;
                    flushNext();
                }
            };
            //------------------------------------------------------------------
            // onStreamProgress(jsonChunk):
            //   - Extract the token
            //   - process it (state machine, rolling buffer)
            //   - add the resulting flushList to the global flushQueue
            //   - schedule flush if not already in progress
            //------------------------------------------------------------------
            const onStreamProgress = (jsonChunk: any) => {
                let token = jsonChunk.choices[0].delta.content;

                if (token !== null && token !== undefined) {
                    if (mode==="think") {
                        processToken("</think>")
                        // console.log('end think')
                    }
                    mode = "normal";

                }

                if (token === undefined) {
                    if (jsonChunk.choices[0].delta.reasoning_content !== undefined) {
                        if(mode === "normal") {
                            processToken("<think>")
                        }
                        mode = "think";
                        token = jsonChunk.choices[0].delta.reasoning_content
                    } else {
                        token = ""
                    }
                }


                console.log('mode: ' + mode + "    token: " + token)
                // console.log(jsonChunk)
                const flushList = processToken(token);
                flushList.forEach(item => flushQueue.push(item));
                scheduleFlush();
            };

            let ccindex = 0

            // A variable to store how many characters we've processed from the raw response
            let lastIndex = 0;
            // A buffer string for partial JSON data that hasn't yet formed a valid chunk
            let chunkBuffer = "";

            // The rest of your XHR logic:
            xhr.onprogress = function () {
                // 1) Get new data from responseText since the last processed index
                let newData = xhr.responseText.substring(lastIndex);
                lastIndex = xhr.responseText.length;

                // 2) Accumulate into our buffer
                chunkBuffer += newData;

                // 3) Try to parse out as many JSON objects as we can
                const {allResponses, buffer} = getAllChunks(chunkBuffer);// console.log(allChunks)

                if (allResponses.length > 0) {
                    let s = JSON.stringify(allResponses);
                    ccindex += s.length // enclosing
                }

                // for (let i = 0; i < allResponses.length; i++) {
                //     const chunk = allResponses[i];
                //     if (!chunk || !chunk.choices) {
                //         continue;
                //     }

                    // 4) For each valid JSON chunk we managed to parse, process it
                    for (let i = 0; i < allResponses.length; i++) {
                        const chunk = allResponses[i];
                        if (!chunk || !chunk.choices) {
                            continue;
                        }
                        if (chunk.choices[0].finish_reason === 'tool_call') {
                            textField.textContent += chunk.choices[0].delta.content;
                        }
                        if (chunk.choices[0].finish_reason === 'stop' || chunk.choices[0].finish_reason === 'tool_call') {
                            const timings = chunk.timings;
                            let model = chunk.model;
                            if (model) {
                                model = model.split('/').slice(-1);
                            }

                            if (timings) {
                                const timing = document.getElementById('timing-info') as HTMLElement;
                                timing.innerText = `${model}: ${round(1000.0 / timings.predicted_per_token_ms, 1)} t/s `;
                            }
                            textField.innerHTML = parseMessage(textField.innerText)
                            // highlightCode(textField);
                            inputElement.contentEditable = "true";
                            stopButton.disabled = true;
                            loadHistory();
                            inputElement.focus();
                            for (const elem1 of document.getElementsByClassName('shimmer') as any) {
                                elem1.classList.remove('shimmer');
                            }
                            //
                            if(editor && lineNumber > 1 && lineNumber < editor.state.doc.lines) {
                                removeLinesAfter(editor, lineNumber)
                            }
                            // console.log(editor, lineNumber)
                            return;
                            // break;
                        } else {
                            onStreamProgress(chunk);
                        }
                    }

                    // 5) Keep any leftover partial JSON in chunkBuffer
                    //    (which is the ‘buffer’ value returned by getAllChunks)
                    chunkBuffer = buffer;
                    updateScrollButton();
                // }
            };


            xhr.addEventListener("error", function (e) {
                console.log("error: " + e);
            });

            xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");

            const formData = getFormDataAsJSON('settings-form')

            //
            const content = editor!.state.doc.toString().trim();
            if (content && canvasEnabled) {
                m += '\n';
                m += "<codecanvas>";
                m += content;
                m += "</codecanvas>"
                console.log("Inserting canvas")
            } else {
                console.log("Ignoring empty canvas")
            }

            formData.input = m
            formData.pruneHistoryIndex = pruneHistoryIndex;

            xhr.send(JSON.stringify(formData));
        }
    }

    return handleInput
}

// reset settings handling
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

//
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

//
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

// menu for chat or collections
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
    for (let elem of document.getElementsByClassName('mode-button') as any) {
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

            textNode.textContent = target.textContent;
            updateUrlParam(target.id)
        })
        //update current selection
        if (selectedMode && elem.id === selectedMode) {
            // console.log('sekect ', elem)
            (elem as HTMLAnchorElement).click();
            menu.classList.add('hidden');
        }
    }
}

//
function setupTextInput() {
    const textInput = document.getElementById('input-box')! as HTMLDivElement;
    if (textInput) {
        textInput.addEventListener('keypress', getInputHandler(textInput))
    }

    setFocusToInputField(textInput);
}

//
const setupEscapeButtonForPopups = () => {
    document.addEventListener('keydown', function (event) {
        // close popups on escape key
        if (event.key === 'Escape') {
            // Remove the hash from the URL to close the element opened via CSS anchors
            window.location.hash = '';
        }
    });
};

// enforce
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

//
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

// show/hide sidebar or code editor
const updateHeaderAndContentWidth = () => {
    const sidebar = document.querySelector('.sidebar') as HTMLElement;
    const header = document.querySelector('.header') as HTMLElement;
    const content = document.querySelector('.content') as HTMLElement;

    const sidebarWidth = "300px"
    const maxWidth = sidebar.classList.contains("hidden") ? "100vw" : `calc(100vw - ${sidebarWidth})`;
    content.style.width = maxWidth
    header.style.width = maxWidth
}

// show/hide sidebar or code editor
const toggleRightPanel = (force?: boolean | undefined) => {
    const rightPanel = document.querySelector('.right-panel') as HTMLElement;
    const sidebar = document.querySelector('.sidebar') as HTMLElement;

    if (rightPanel.style.display === 'none' || rightPanel.style.display === '' || force) {
        rightPanel.style.display = 'block';
        sidebar.classList.add('hidden');
    } else {
        rightPanel.style.display = 'none';
        sidebar.classList.remove('hidden');
    }
    updateHeaderAndContentWidth()
};

// show/hide sidebar or code editor
const toggleSidebar = (force?: boolean) => {
    // e.preventDefault();
    const sidebar = document.querySelector('.sidebar') as HTMLElement;
    if (force) {
        sidebar.classList.remove('hidden');
    } else {
        sidebar.classList.toggle('hidden');
    }
    updateHeaderAndContentWidth()
};

//
function setupEditor() {
    const initialText = ''
    const targetElement = document.querySelector('#editor')!
    let language = new Compartment;

    const softwrap = new Compartment();

    editor = new EditorView({
        doc: initialText,

        extensions: [
            basicSetup,
            lineNumbers(),
            softwrap.of([]),
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


    const button = document.createElement('button');
    button.id = 'linewrap-toggler'
    button.innerText = "Line Wrapping: Off";
    const rightPanel = document.querySelector('.right-panel')
    rightPanel!.insertAdjacentElement('afterbegin', button);

    let wrapping = false;
    button.addEventListener('click', () => {
      wrapping = !wrapping;
      button.innerText = `Line Wrapping: ${wrapping ? 'On' : 'Off'}`;

      editor!.dispatch({
        effects: [softwrap.reconfigure(
          wrapping ? EditorView.lineWrapping : []
        )]
      });
    })

    editor.dom.addEventListener('input', debounce(detectAndSetMode, 500));

    function detectAndSetMode() {
        const content = editor!.state.doc.toString();

        const result = hljs.highlightAuto(content, languageSubset);
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
    }
}


function setupSidebarAndEditorToggle() {
    document.getElementById("sidebar-toggler")!.addEventListener("click", () => {
        toggleSidebar()
    })
    document.getElementById("right-panel-toggler")!.addEventListener("click", () => {
        toggleRightPanel()
    })
}

// const setupProjects = () => {
//     const newProjectButton = document.getElementById('new-project-button') as HTMLButtonElement;
//     newProjectButton.onclick = createProject;
// };

const main = () => {
    //
    setupSidebarAndEditorToggle();

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

    setupEditor();

    // setupProjects()
}

// let selectedProjectId = null;
//
// function loadChatsForProject(projectId) {
//   fetch(`/api/chats?project_id=${projectId}`).then(res => res.json()).then(chats => {
//     const list = document.getElementById('chat-list')!;
//     list.innerHTML = '';
//     chats.forEach(chat => {
//       const item = document.createElement('li');
//       item.innerText = chat.title || 'Untitled Chat';
//       item.onclick = () => loadChat(chat.chat_id);
//       list.appendChild(item);
//     });
//   });
// }
//
// function loadProjects() {
//   fetch('/api/projects').then(res => res.json()).then(projects => {
//     const list = document.getElementById('project-list');
//     if(!list) {
//         return;
//     }
//     list.innerHTML = '';
//     projects.forEach(project => {
//       const item = document.createElement('li');
//       item.innerText = project.name;
//       item.onclick = () => {
//         selectedProjectId = project.id;
//         loadChatsForProject(project.id);
//       };
//       list.appendChild(item);
//     });
//   });
// }
//
// const createProject = () => {
//   const name = prompt("Project name:");
//   if (!name) return;
//   fetch('/api/projects', {
//     method: 'POST',
//     body: JSON.stringify({ name }),
//     headers: { 'Content-Type': 'application/json' }
//   }).then(() => loadProjects());
// };


// typical debounce
function debounce(fn: any, delay: number) {
    let timeout: number;
    return function (...args: any[]) {
        clearTimeout(timeout);
        // @ts-ignore
        timeout = window.setTimeout(() => fn.apply(this, args), delay);
    }
}


main();
