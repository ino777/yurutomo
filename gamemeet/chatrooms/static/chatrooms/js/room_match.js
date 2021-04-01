
const app = new Vue({
    delimiters: ['[[', ']]'],
    el: "#app",
    data: {
        url: {
            register: registerUrl,
            unregister: unregisterUrl,
            getMatchRoom: getMatchRoomUrl,
            confirm: confirmUrl,
            cancel: cancelUrl,
            isCompleted: isCompletedUrl
        },
        param: {},
        csrftoken: null,

        showMatching: true,
        showConfirm: false,

        roomId: '',
        roomUrl: '',

        timer: {
            matchingWaitTimerId: null,
            confirmDisplayTimerId: null,
            completeWaitTimerId: null,
        }
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
    },

    methods: {
        //
        //  this でVueインスタンスにアクセスできるように、コールバック関数はアロー関数にしている
        //


        // マッチング登録
        start: function () {
            axios.post(this.url.register, {
                condition: {
                    game_name: "Test game",
                    number: 2
                }
            }, {
                headers: { "Content-type": "application/json", "X-CSRFToken": this.csrftoken },
            })
                .then((result) => {
                    console.log(result.data);
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
            this.showConfirm = false;
            this.showMatching = true;

            // マッチングをやめる
            this.clearAllTimer();

            axios.post(this.url.unregister, {}, {
                headers: { "Content-type": "application/json", "X-CSRFToken": this.csrftoken }
            })
                .then((result) => {
                    console.log(result.data);
                    if (result.data.is_unregistered) {
                        console.log("quit");
                    }
                })
                .catch((error) => {
                    console.log(error);
                })
        },

        // マッチング承認
        confirm: function () {
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
            this.showMatching = true;
            this.timer.matchingWaitTimerId = setInterval((function getRoomId() {
                axios.get(this.url.getMatchRoom)
                    .then((result) => {
                        // マッチングした場合
                        if (result.data.room_id) {
                            this.roomId = result.data.room_id;
                            this.roomUrl = result.data.room_url;
                            console.log(this.roomId);
                            clearInterval(this.timer.matchingWaitTimerId);

                            // 最長10秒間承認ボタンを表示
                            this.showMatching = false;
                            this.showConfirm = true;
                            this.timer.confirmDisplayTimerId = setTimeout(this.quit, 10000);
                        }
                    })
                    .catch((error) => {
                        console.log(error);
                        this.quit();
                    })
                return getRoomId;
            }).bind(this), interval)
        },

        // マッチング承認を待つ
        setCompleteWaitTimer: function (interval) {
            this.showConfirm = true;
            this.showMatching = false;
            this.timer.completeWaitTimerId = setInterval((function getMatchCompleted() {
                axios.get(this.url.isCompleted, {
                    params: {
                        room_id: this.roomId
                    }
                })
                    .then((result) => {
                        // 誰かがキャンセルしたとき
                        if (result.data.is_cancelled) {
                            console.log("CANCELLED");
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
                            console.log("COMPLETE!");

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
            }).bind(this), interval)
        }
    },

    beforeDestroy() {
        this.clearAllTimer();
    }
})
