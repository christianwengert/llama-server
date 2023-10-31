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

const run = () => {

        const chat = document.getElementById('chat')!;
        const stopButton = document.getElementById('stop-generating')! as HTMLButtonElement;
        if (stopButton) {
            stopButton.disabled = true;
        }
        const resetButton = document.getElementById('reset-button') as HTMLElement;
        if (resetButton) {
            resetButton.addEventListener('click', (e) => {
                e.preventDefault();
                fetch('/reset').then(() => {
                    document.location.reload(); // todo
                })
            })
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
                let openBraces = 0;
                let lastProcessedIndex = 0;

                xhr.onreadystatechange = function () {
                    if (xhr.readyState == 3 || xhr.readyState == 4) {
                        const newResponseText = xhr.responseText.substring(lastProcessedIndex);
                        lastProcessedIndex = xhr.responseText.length;
                        buffer += newResponseText;

                        let startPos = 0;
                        for (let i = 0; i < buffer.length; i++) {
                            if (buffer[i] === '{') openBraces++;
                            if (buffer[i] === '}') openBraces--;

                            if (openBraces === 0) {
                                const jsonStr = buffer.substring(startPos, i + 1);
                                const jsonObj = JSON.parse(jsonStr);

                                if (jsonObj.stop) {
                                    const timings = jsonObj.timings
                                    let model = jsonObj.model
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
                                }

                                // const elem = document.getElementById('elem');
                                if (elem && jsonObj.content) {
                                    if (inner.innerText === "") {
                                        jsonObj.content = jsonObj.content.trimStart()
                                    }
                                    inner.innerText += jsonObj.content;
                                }
                                if (inner.querySelector('.loading')) {
                                    inner.innerHTML = "";
                                }

                                buffer = buffer.substring(i + 1);
                                i = -1;
                                startPos = 0;
                                openBraces = 0;
                            }
                        }
                    }


                    // if (xhr.readyState == 3) {  // streaming
                    //     // we might receive many tokens at once, so we need to split them and apply them
                    //     const packages = xhr.response.substring(seenBytes).split('}{');
                    //     for (let p of packages) {
                    //         if (!p.startsWith('{')) {
                    //             p = '{' + p + '}';
                    //         }
                    //         let newData;
                    //         try {
                    //             newData = JSON.parse(p);
                    //         } catch (e) {
                    //             console.log(e, p)
                    //         }
                    //
                    //         if (inner.querySelector('.loading')) {
                    //             inner.innerHTML = "";
                    //         }
                    //         if (seenBytes == 0) {
                    //             newData.content = newData.content.trimStart()
                    //         }
                    //         inner.innerHTML += newData.content;
                    //     }
                    //     seenBytes = xhr.responseText.length;
                    // }
                    // if (xhr.readyState == 4) {  // done
                    //
                    //     // now last seen bytes is not correct
                    //     // this string is prepended (the last one)
                    //     // '{"content": "", "stop": false}'
                    //     // the following code gets rid of it if available
                    //     // const unusedPart = '{"content": "", "stop": false}'
                    //     // const a = xhr.response.substring(lastProcessedIndex).indexOf('}{')
                    //     // if (a >= 0) {
                    //     //     seenBytes += a + 1;
                    //     // }
                    //
                    //     const data = xhr.response.substring(lastProcessedIndex);
                    //
                    //     const timings = JSON.parse(data).timings
                    //     let model = JSON.parse(data).model
                    //     if (model) {
                    //         model = model.split('/').slice(-1);
                    //     }
                    //
                    //     const timing = document.getElementById('timing-info')! as HTMLSpanElement;
                    //     timing.innerText = `${round(timings.predicted_per_second, 1)} Tokens per second (${round(timings.predicted_per_token_ms, 1)}ms per token (${model})) `
                    //
                    //     textInput.contentEditable = "true";
                    //     stopButton.disabled = true;
                    //     // adapt markdown for ```
                    //     const pattern = /```([a-z]+)? ?([^`]*)```/g
                    //     const rep = `<div class="code-header"><div class="language">$1</div><div class="copy">Copy</div></div><pre><code class="language-$1">$2</code></pre>`
                    //     const intermediate = inner.innerText.replace(pattern, rep)
                    //     // adapt markdown for `
                    //     const pattern2 = /`([^`]*)`/g
                    //     const rep2 = `<code class="inline">$1</code>`
                    //     inner.innerHTML = intermediate.replace(pattern2, rep2)
                    //
                    //     scrollToBottom()
                    //     // highlight code
                    //     inner.querySelectorAll('pre code').forEach((block) => {
                    //         hljs.highlightElement(<HTMLElement>block);
                    //     });
                    //     // set up copy to clipboard buttons
                    //     inner.querySelectorAll('.code-header >.copy').forEach((copyElem) => {
                    //         copyElem.addEventListener('click', (copyEvent) => {
                    //             copyEvent.preventDefault();
                    //             const target = copyEvent.target! as HTMLElement;
                    //
                    //             const t = (target.parentElement!.nextElementSibling! as HTMLElement).innerText;
                    //             // Copy the text inside the text field
                    //             navigator.clipboard.writeText(t).then(() => {
                    //             });
                    //             target.innerText = 'Copied'
                    //             target.style.cursor = 'auto'
                    //
                    //             setInterval(() => {
                    //                 target.innerText = 'Copy'
                    //                 target.style.cursor = 'pointer'
                    //             }, 3000)
                    //         })
                    //     })
                    //     textInput.focus()
                    // }
                }
                ;

                xhr.addEventListener("error", function (e) {
                    console.log("error: " + e);
                });
                xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");

                const formData = getFormDataAsJSON('settings-form')
                // console.log(formData)
                formData.input = m
                // @ts-ignore
                formData.stop = formData.stop.split(',')

                xhr.send(JSON.stringify(formData));
            }
        }

        setFocusToInputField(textInput);
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
