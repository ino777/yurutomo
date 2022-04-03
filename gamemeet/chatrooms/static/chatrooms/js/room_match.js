
const app = new Vue({
    delimiters: ["[[", "]]"],
    el: "#room-match",
    data: {
        url: {
            popularTopics: popularTopicsUrl,
            searchTopics: searchTopicsUrl,
            createTopic: createTopicUrl,

            register: registerUrl,
            unregister: unregisterUrl,
            getMatchRoom: getMatchRoomUrl,
            confirm: confirmUrl,
            cancel: cancelUrl,
            isCompleted: isCompletedUrl
        },
        param: {},
        csrftoken: null,

        // マッチング待ち中か
        isMatching: false,

        showMatching: true,
        showWaiting: false,
        showConfirm: false,

        lifeGuageWidth: 100,
        lifeBar: document.getElementById('life-progressbar'),

        roomId: "",
        roomUrl: "",

        timer: {
            matchingMessageTimerId: null,
            lifeGuageTimerId: null,

            matchingWaitTimerId: null,
            confirmDisplayTimerId: null,
            completeWaitTimerId: null,
        },

        matchingMessageText: "",

        // topic関連
        popularTopics: [],
        searchText: "",
        searchResult: [],

        newTopic: "",
        newTopicError: "",

        topic: "",
        number: 0,
        numberLimit: 10,

    },

    created: function () {
        // csrf_tokenの取得
        // 引用： https://docs.djangoproject.com/en/3.1/ref/csrf/
        this.csrftoken = function getCookie(name) {
            let cookieValue = null;
            if (document.cookie && document.cookie !== "") {
                const cookies = document.cookie.split(";");
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    // Does this cookie string begin with the name we want?
                    if (cookie.substring(0, name.length + 1) === (name + "=")) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }("csrftoken");

        // マッチング登録状況をリセットする
        this.quit();
        this.matchingMessageText = "";
    },
    computed: {
        // マッチングボタン押せない
        btnDisable: function () {
            return (this.topic.length == 0) || (this.number <= 0)
        }
    },

    methods: {
        //
        //  this でVueインスタンスにアクセスできるように、コールバック関数はアロー関数にしている
        //

        // マッチングメッセージを一定時間表示
        flashMatchingMessage: function (text, time = 3000) {
            this.matchingMessageText = text;
            this.matchingMessageTimerId = setTimeout(() => {
                this.matchingMessageText = "";
            }, time);
        },

        // topicを取得
        getPopularTopics: function () {
            axios.get(this.url.popularTopics, {
                params: {}
            }).then((result) => {
                this.popularTopics = result.data.topics;
            })
        },

        // topicを検索
        searchTopics: function (event, text = "") {
            if (text.length == 0 && this.searchText.length == 0) {
                this.searchResult = [];
                return;
            }

            axios.get(this.url.searchTopics, {
                params: {
                    search_text: text || this.searchText,
                }
            }).then((result) => {
                this.searchResult = result.data.topics;
            })
        },

        // topicを追加
        createTopic: function () {
            this.newTopic = this.newTopic.trim();
            if ((this.newTopic.length <= 0) || (this.newTopic.length > 255)) {
                console.log("Invalid name length");
                return;
            }
            axios.post(this.url.createTopic, {
                name: this.newTopic,
            }, {
                headers: { "Content-type": "application/json", "X-CSRFToken": this.csrftoken },
            })
                .then((result) => {
                    if (!result.data.is_created) {
                        this.newTopicError = "※そのトピックは既に存在します";
                        return;
                    }

                    this.newTopicError = "";
                    this.setTopic(this.newTopic);
                    // モーダルを閉じる
                    const m = document.querySelector(".modal");
                    UIkit.modal(m).hide();

                })
        },

        // topicをセット
        setTopic: function (name) {
            this.topic = name;
        },

        // 長い名前は後半を切り捨てる
        cleanTopicName: function (name) {
            let cleanedName = name.toString();
            if (cleanedName.length >= 31) {
                cleanedName = cleanedName.slice(0, 30) + "...";
            }
            return cleanedName;
        },

        startLifeGuage: function () {
            this.lifeBar = document.getElementById('life-progressbar');
            this.lifeBar.value = 100;

            const totalTime = 10000;
            let speed = this.lifeBar.value / totalTime * 1.1;

            this.timer.lifeGuageTimerId = setInterval(() => {

                if (this.lifeBar.value < 0) {
                    clearInterval(this.timer.lifeGuageTimerId);
                    return;
                }
                this.lifeBar.value -= speed * 100;
            }, 100)
        },

        stopLifeGuage: function () {
            clearInterval(this.timer.lifeGuageTimerId);
        },

        // マッチング登録
        start: function () {
            this.isMatching = true;

            axios.post(this.url.register, {
                condition: {
                    topic: this.topic,
                    number: this.number
                }
            }, {
                headers: { "Content-type": "application/json", "X-CSRFToken": this.csrftoken },
            })
                .then((result) => {
                    if (!result.data.is_registered) {
                        return;
                    }
                    // マッチング待ち
                    // 2秒ごとにマッチングしてないか確認
                    this.setMatchingWaitTimer(2000);
                })
                .catch((error) => {
                    console.log(error);
                })
        },

        // マッチング登録解除
        quit: function () {
            this.isMatching = false;
            this.showConfirm = false;
            this.showWaiting = false;
            this.showMatching = true;

            // マッチングをやめる
            this.clearAllTimer();

            this.flashMatchingMessage("マッチングをキャンセルしました");

            axios.post(this.url.unregister, {}, {
                headers: { "Content-type": "application/json", "X-CSRFToken": this.csrftoken }
            })
                .then((result) => {
                    //
                })
                .catch((error) => {
                    console.log(error);
                })
        },

        // マッチング承認
        confirm: function () {
            this.stopLifeGuage();
            axios.post(this.url.confirm, {}, {
                headers: { "Content-type": "application/json", "X-CSRFToken": this.csrftoken }
            })
                .then((result) => {
                    console.log(result.data);
                    if (!result.data.is_confirmed) {
                        return;
                    }

                    // 承認待ち
                    // 1秒ごとにマッチング承認を確認
                    this.setCompleteWaitTimer(1000);
                })
                .catch((error) => {
                    console.log(error);
                })
        },

        // マッチング承認をキャンセル
        cancelConfirm: function () {
            this.stopLifeGuage();
            return axios.post(this.url.cancel, {}, {
                headers: { "Content-type": "application/json", "X-CSRFToken": this.csrftoken }
            })
        },

        // マッチング辞退
        cancel: function () {
            this.quit();
        },

        // タイマー中のすべてのタイマーを止める
        clearAllTimer: function () {
            Object.keys(this.timer).map((key) => {
                clearInterval(this.timer[key]);
                clearTimeout(this.timer[key]);
            });
        },

        //
        clearDisplayTimer: function () {
            clearTimeout(this.timer.confirmDisplayTimerId);
        },

        // マッチングを待つ
        setMatchingWaitTimer: function (interval) {
            this.showConfirm = false;
            this.showMatching = false;
            this.showWaiting = true;
            this.timer.matchingWaitTimerId = setInterval((getRoomId = () => {
                axios.get(this.url.getMatchRoom)
                    .then((result) => {
                        // マッチングした場合
                        if (result.data.is_matched) {
                            this.roomId = result.data.room_id;
                            this.roomUrl = result.data.room_url;
                            clearInterval(this.timer.matchingWaitTimerId);

                            // 最長10秒間承認ボタンを表示
                            this.showMatching = false;
                            this.showWaiting = false;
                            this.showConfirm = true;
                            this.startLifeGuage();
                            this.timer.confirmDisplayTimerId = setTimeout(this.quit, 10000);
                        }
                    })
                    .catch((error) => {
                        console.log(error);
                        this.quit();
                    })
                return getRoomId;
            })(), interval)
        },

        // マッチング承認を待つ
        setCompleteWaitTimer: function (interval) {
            this.showConfirm = true;
            this.showMatching = false;
            this.showWaiting = false;
            this.timer.completeWaitTimerId = setInterval((getMatchCompleted = () => {
                axios.get(this.url.isCompleted, {
                    params: {
                        room_id: this.roomId
                    }
                })
                    .then((result) => {
                        // 誰かがキャンセルしたとき
                        if (result.data.is_cancelled) {
                            this.flashMatchingMessage("他のユーザーがキャンセルしました");

                            clearInterval(this.timer.completeWaitTimerId);

                            // 自分も承認をキャンセル
                            this.cancelConfirm()
                                .then((result) => {
                                    console.log(result.data);
                                    if (result.data.is_cancelled) {
                                        // 再びマッチング待ち
                                        this.setMatchingWaitTimer(2000);
                                        return;
                                    }
                                })

                        }
                        // マッチング完了したとき
                        if (result.data.is_completed) {
                            clearInterval(this.timer.completeWaitTimerId);

                            // ルームへ移動
                            location.href = this.roomUrl;
                            return;
                        }
                    })
                    .catch((error) => {
                        console.log(error);
                        this.quit();
                    })
                return getMatchCompleted;
            })(), interval)
        }
    },
    mounted: function () {
        this.getPopularTopics();
    },

    beforeDestroy() {
        this.quit();
    }
})
