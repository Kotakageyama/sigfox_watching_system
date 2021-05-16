# sigfox_watching_system
# 卒研で作った見守りシステム
学校の卒業研究で作りました。大学に行ったら個人で開発していきます。
独居老人の増加と孤独死の増加のため、手軽に導入できるIoTシステムを考えた。老人宅の場合、インターネットをひいていないことが多いため、LPWAのSigfox通信を使うことで、コスト削減を図った。
また、孤独死を早めに感知することで部屋の清掃費用を減らせるため不動産でも使えたり、心筋梗塞や脳梗塞を感知することで素早い対応が可能になり医療分野でも使えると考える。この二点の感知は未実装である。

エッジ側で、ラズパイと温湿度センサを利用して部屋の環境をモニタリングし、温度が高いと警告を鳴らしたり、安否確認のためにブザーを鳴らす。適時Sigfox通信してデータをクラウドに送る。
クラウド側で、djangoで作成したアプリケーションで息子夫婦が老人の部屋の状況をスマホから確認できる。
# 実際に動かしているサーバ
http://iroha17.pythonanywhere.com でアプリケーションを動かしています。
- login ted13@darshasilje.sakura.ne.jp
- pass aiueo89op
