let num = 0;
const room = new Vue({
    delimiters: ['[[', ']]'],
    el: "#room",
    components: {
    },
    data: {
        isMounted: false,

        // デバイス情報
        audios: [],
        videos: [],
        selectedAudio: "",
        selectedVideo: "",

        // Peer
        peerId: "",

        // Room
        roomId: roomId,
        roomMode: "sfu", // sfu or mesh

        // Roomメンバーの情報
        // Peer ID とユーザーネームの対応表
        memberNames: memberNames,

        // ストリーム
        localStream: {    // 自分のストリーム
            stream: null,
            onSound: false,
            isMuted: false,
            audioContext: null,
        },
        streams: {},       // 相手（複数）のストリーム
        soundThreshold: 0.01,

        // チャット
        myText: "",         // 自分のテキスト
        messages: [],       // チャット欄


        // テキストエリアの高さ
        // テキストエリアが可変なため、１つ前の状態の高さも保持する
        prevTextareaHeight: document.querySelector(".textarea-container").clientHeight,
        textareaHeight: document.querySelector(".textarea-container").clientHeight,
    },
    computed: {
        messageHeight: function () {
            return "calc(100% - " + this.textareaHeight + "px)";
        },
    },
    watch: {
        // テキストの入力を検知して、テキストエリアの高さを取得する
        myText: {
            // 初期化のタイミングで実行
            immediate: true,
            handler() {
                // レンダリングを一度待つ
                this.$nextTick(function () {
                    this.prevTextareaHeight = this.textareaHeight;
                    this.textareaHeight = document.querySelector(".textarea-container").clientHeight;
                })
            }
        },
        // テキストエリアの高さの変化を検知して、メッセージ欄をスクロールする
        textareaHeight: function () {
            let deltaHeight = this.textareaHeight - this.prevTextareaHeight
            if (deltaHeight > 0) {
                // レンダリングを一度待つ
                this.$nextTick(function () {
                    document.querySelector(".messages-container").scrollBy(0, deltaHeight);
                })
            } else {
                document.querySelector(".messages-container").scrollBy(0, deltaHeight);
            }
        }
    },
    methods: {
        // 発言中かを判定
        detectSound: function (stream) {
            if (stream.audioContext) {
                // 既にあれば閉じる
                stream.audioContext.close();
            }
            stream.audioContext = new AudioContext();
            const scriptProcessor = stream.audioContext.createScriptProcessor(0, 1, 1);
            const mediaStreamSrc = stream.audioContext.createMediaStreamSource(stream.stream);
            mediaStreamSrc.connect(scriptProcessor);
            scriptProcessor.onaudioprocess = (e) => {
                const input = e.inputBuffer.getChannelData(0);
                let sum = 0;
                let vomule = 0;
                for (i = 0; i < input.length; i++) {
                    sum += input[i] * input[i];
                }
                volume = Math.sqrt(sum / input.length);

                // volume が閾値より大きければストリームの onSound プロパティを true に
                this.$set(stream, "onSound", volume > this.soundThreshold);
            }
            scriptProcessor.connect(stream.audioContext.destination);
        },

        // 自身のストリームをセットする
        setLocalStream: function (constraints) {
            navigator.mediaDevices.getUserMedia(constraints)
                .then(stream => {
                    // 成功時
                    this.$set(this.localStream, "stream", stream);

                    // ミュート設定
                    if (this.localStream.isMuted) {
                        this.muteStream(this.localStream);
                    }

                    // 発言中かを判定
                    this.detectSound(this.localStream)

                }).catch(error => {
                    // 失敗時にはエラーログを出力
                    console.error('mediaDevice.getUserMedia() error:', error);
                    return;
                });
        },

        // 使用デバイス変更時
        onDeviceChange: function () {
            // 選択したデバイスがあればそのデバイスを使う
            // 選択したデバイスがない場合はミュート
            const constraints = {
                // video: this.selectedVideo ? { deviceId: { exact: this.selectedVideo } } : true,
                video: false,
                audio: this.selectedAudio ? { deviceId: { exact: this.selectedAudio } } : false,
            }
            this.setLocalStream(constraints);
        },

        // ミュートの切り替え
        switchMute: function (stream) {
            this.$set(stream, "isMuted", !stream.isMuted);
            this.muteStream(stream);
        },

        // ストリームをミュート
        muteStream: function (stream) {
            stream.stream.getAudioTracks().forEach((track) => (track.enabled = !stream.isMuted));
        },

        // メッセージを送信
        sendMessage: function () {
            if (this.myText.trim().length == 0) { return; }

            // テキストをルームに送信
            this.room.send(this.myText);

            this.messages.push(
                {
                    type: "message",
                    srcUser: this.memberNames[this.peer.id],
                    data: this.myText
                }
            )

            this.myText = "";
        },

        // ルームを退出
        leaveRoom: function () {
            this.room.close();
            location.href = indexUrl;
        },

        // ルームのログを得る
        getLog: function () {
            this.room.getLog();
        },

        // 長い名前は後半を切り捨てる
        truncateName: function (name) {
            name = name.toString()
            if (name.length >= 21) {
                name = name.slice(0, 20) + "...";
            }
            return name
        }


    },
    mounted: async function () {

        this.isMounted = true;

        // デバイスの一覧を取得
        const devices = await navigator.mediaDevices.enumerateDevices();

        devices.filter(device => device["kind"] == "audioinput").map(audio => this.audios.push(audio))
        devices.filter(device => device["kind"] == "videoinput").map(video => this.videos.push(video))

        // 自身のカメラ映像取得
        this.setLocalStream({ video: false, audio: true });


        // Peer 作成
        this.peer = new Peer(userId, {
            key: "43a3ef08-82b6-4c24-b93d-c6316e07c4ff",
            debug: 3
        })

        // Peer Open処理
        this.peer.on("open", () => {
            this.peerId = this.peer.id;
        })

        // Peer Error処理
        this.peer.on("error", error => console.error(error));

        // 1秒後に実行
        setTimeout(() => {

            if (!this.peer.open) {
                console.error("peer open error.")
                return;
            }

            if (!this.roomId) {
                console.error("invalid roomId.")
                return;
            }
            // ルーム参加
            this.room = this.peer.joinRoom(this.roomId, {
                mode: this.roomMode,
                stream: this.localStream.stream,
            });
            console.log(this.room);

            // ルーム入室時処理
            this.room.once("open", () => {
                // ルーム内に参加している人を streams に登録
                this.room.members.forEach(member => {
                    this.$set(this.streams, member, { stream: null, onSound: false, isMuted: false })
                });

                this.messages.push(
                    {
                        type: "log",
                        data: "=== You joined === ",
                    }
                )
            });

            // ルーム退出時処理
            this.room.once("close", () => {
                // streams を初期化
                this.streams = {};

                this.messages.push(
                    {
                        type: "log",
                        data: "=== You left === ",
                    }
                )
            });

            // 他の人がルーム入室時処理
            this.room.on("peerJoin", peerId => {
                // streams に追加
                this.$set(this.streams, peerId, { stream: null, onSound: false, isMuted: false })

                this.messages.push(
                    {
                        type: "log",
                        data: `=== ${peerId} joined === `,
                    }
                )
            });

            // 他の人がルーム退出時処理
            this.room.on("peerLeave", peerId => {
                // streams から削除
                this.$delete(this.streams, peerId)

                this.messages.push(
                    {
                        type: "log",
                        data: `=== ${peerId} left === `,
                    }
                )
            });

            // ストリーム受信時処理
            this.room.on("stream", stream => {
                // 受信したストリームを streams にセット
                this.$set(
                    this.streams, stream.peerId,
                    {
                        stream: stream,
                        onSound: false,
                        isMuted: false,
                        audioContext: null,
                        id: stream.peerId,
                    }
                )

                // // ミュート設定
                // if (this.streams[stream.peerId].isMuted) {
                //     this.muteStream(this.streams[stream.peerId]);
                // }

                // 発言中かを判定
                this.detectSound(this.streams[stream.peerId])
            });


            // データ受信時処理
            this.room.on("data", ({ src, data }) => {
                let srcUser = this.memberNames[src];

                this.messages.push(
                    {
                        type: "message",
                        srcUser: srcUser,
                        data: data,
                    }
                )
            })

            // ルームのログ受信時処理
            this.room.once("log", logs => {
                for (const logStr of logs) {
                    const { messageType, message, timestamp } = JSON.parse(logStr);
                    this.messages.push(
                        {
                            type: "log",
                            data: `=== ${messageType} -- ${message} -- ${timestamp} === `
                        }
                    )
                }
            });
        }, 1000);
    }
})