const chatTextarea = {
    data() {
        return {
        }
    },
    model: {
        prop: "myText",
    },
    props: {
        myText: String,
    },
    template: `<div class="text-box">
               <div class="text-dummy" aria-hidden="true">{{myText + "\u200b"}}</div>
               <textarea id="my-text" :value="myText" @input="$emit('input', $event.target.value)" placeholder="Message"></textarea>
               </div>`
}