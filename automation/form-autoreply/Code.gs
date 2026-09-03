/**
 * RAS® セッション申込フォーム 自動化スクリプト
 *
 *  1. 申込があると、申込者へ自動返信メールを送る
 *  2. 希望日時を読み取り、Googleカレンダーに予定を作成する
 *  3. 主催者にも通知メールを送る（日時が読み取れない場合は「要確認」として通知）
 *
 * 設置手順は README.md を参照。
 * 設問名が変わっても動くよう、キーワードで項目を自動判別しています。
 */

// ===================== 設定 =====================
var CONFIG = {
  // 予定を入れるカレンダーID（Googleカレンダーの「設定と共有」で確認できます）
  CALENDAR_ID: 'xakemix789@gmail.com',

  // 主催者（通知メールの宛先。空にすると通知しません）
  OWNER_EMAIL: 'xakemix789@gmail.com',

  // 自動返信メールの差出人名
  SENDER_NAME: 'RAS® 及川明美',

  // 返信先アドレス（空ならスクリプト実行者のアドレス）
  REPLY_TO: '',

  // セッションの所要時間（分）
  SESSION_MINUTES: 60,

  // 日付だけで時刻が取れなかったときに仮置きする開始時刻（時, 分）
  FALLBACK_HOUR: 10,
  FALLBACK_MINUTE: 0,

  // 予定に申込者をゲストとして招待するか（trueにするとGoogleから招待メールが届きます）
  INVITE_APPLICANT: false,

  // 予定のリマインダー（分前）。空配列ならカレンダー既定値
  REMINDER_MINUTES: [1440, 60],

  // 予定タイトルの接頭辞
  EVENT_PREFIX: '【RAS体験】',

  // タイムゾーン
  TIMEZONE: 'Asia/Tokyo'
};

// 項目を自動判別するためのキーワード（上から順に照合）
var FIELD_KEYWORDS = {
  email:   ['メールアドレス', 'メール', 'mail', 'e-mail'],
  name:    ['お名前', '氏名', 'name', 'ご芳名'],
  kana:    ['フリガナ', 'ふりがな', 'カナ', 'よみ'],
  phone:   ['電話', 'tel', '携帯', 'phone'],
  date1:   ['第1希望', '第一希望', '希望日', '希望日時', 'ご希望の日', '日程'],
  date2:   ['第2希望', '第二希望'],
  date3:   ['第3希望', '第三希望'],
  time:    ['希望時間', '時間帯', '開始時刻', '時刻'],
  menu:    ['メニュー', 'コース', 'セッション内容', '種類', 'ご希望のセッション'],
  method:  ['オンライン', '対面', '形式', 'zoom', '方法', '会場'],
  note:    ['ご質問', 'ご要望', '備考', 'メッセージ', '相談内容', 'お悩み', '自由記述']
};

// ===================== 初回セットアップ =====================
/**
 * ★ 最初に1回だけ手動で実行してください。
 * ★ 必ず、カレンダーとGmailを使わせたいアカウントでログインした状態で実行すること。
 *   （トリガーは実行した人の権限で動くため、そのアカウントのカレンダーに予定が入り、
 *     そのアカウントのGmailから返信が送られます）
 */
function setup() {
  var form = FormApp.getActiveForm();

  // 既存の同名トリガーを消してから作り直す（二重送信の防止）
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === 'onFormSubmit') {
      ScriptApp.deleteTrigger(triggers[i]);
    }
  }

  ScriptApp.newTrigger('onFormSubmit')
    .forForm(form)
    .onFormSubmit()
    .create();

  // カレンダーに触れるか事前確認
  var cal = CalendarApp.getCalendarById(CONFIG.CALENDAR_ID);
  var calName = cal ? cal.getName() : '★取得できませんでした（CALENDAR_IDと共有設定を確認してください）';

  Logger.log('セットアップ完了。\nフォーム: %s\nカレンダー: %s\n実行アカウント: %s',
    form.getTitle(), calName, Session.getEffectiveUser().getEmail());
}

/** 設問の一覧と自動判別の結果をログに出す確認用関数（任意） */
function debugFields() {
  var items = FormApp.getActiveForm().getItems();
  var titles = [];
  for (var i = 0; i < items.length; i++) {
    titles.push('[' + items[i].getType() + '] ' + items[i].getTitle());
  }
  Logger.log('■ フォームの設問一覧\n' + titles.join('\n'));

  var dummy = {};
  for (var j = 0; j < items.length; j++) dummy[items[j].getTitle()] = '';
  var picked = {};
  for (var key in FIELD_KEYWORDS) picked[key] = pickField_(dummy, FIELD_KEYWORDS[key]) || '(該当なし)';
  Logger.log('■ 自動判別の結果\n' + JSON.stringify(picked, null, 2));
}

// ===================== メイン処理 =====================
function onFormSubmit(e) {
  try {
    var answers = collectAnswers_(e);
    var data = extractData_(answers, e);

    var event = null;
    var eventError = '';
    if (data.startTime) {
      try {
        event = createCalendarEvent_(data);
      } catch (err) {
        eventError = String(err);
      }
    }

    if (data.email) {
      sendAutoReply_(data);
    }
    notifyOwner_(data, event, eventError);

  } catch (err) {
    // 失敗しても申込自体は残るので、主催者に知らせるだけに留める
    if (CONFIG.OWNER_EMAIL) {
      MailApp.sendEmail(CONFIG.OWNER_EMAIL,
        '【要対応】申込フォームの自動処理でエラー',
        'エラー内容:\n' + err + '\n\n' + (err.stack || '') +
        '\n\nフォームの回答を直接ご確認ください。');
    }
    throw err;
  }
}

// ===================== 回答の取り出し =====================
function collectAnswers_(e) {
  var map = {};
  if (!e || !e.response) return map;
  var responses = e.response.getItemResponses();
  for (var i = 0; i < responses.length; i++) {
    var title = String(responses[i].getItem().getTitle()).trim();
    var value = responses[i].getResponse();
    if (Object.prototype.toString.call(value) === '[object Array]') {
      value = value.join(' / ');
    }
    map[title] = value == null ? '' : String(value).trim();
  }
  return map;
}

function extractData_(answers, e) {
  var d = {
    answers: answers,
    email: '',
    name: '',
    kana: '',
    phone: '',
    menu: '',
    method: '',
    note: '',
    rawDate: '',
    rawDate2: '',
    rawDate3: '',
    rawTime: '',
    startTime: null,
    endTime: null,
    allDay: false
  };

  // メールアドレス（フォームの自動収集を最優先）
  if (e && e.response && typeof e.response.getRespondentEmail === 'function') {
    d.email = e.response.getRespondentEmail() || '';
  }
  if (!d.email) d.email = valueOf_(answers, FIELD_KEYWORDS.email);
  if (!d.email) d.email = findEmailAnywhere_(answers);

  d.name     = valueOf_(answers, FIELD_KEYWORDS.name);
  d.kana     = valueOf_(answers, FIELD_KEYWORDS.kana);
  d.phone    = valueOf_(answers, FIELD_KEYWORDS.phone);
  d.menu     = valueOf_(answers, FIELD_KEYWORDS.menu);
  d.method   = valueOf_(answers, FIELD_KEYWORDS.method);
  d.note     = valueOf_(answers, FIELD_KEYWORDS.note);
  d.rawDate  = valueOf_(answers, FIELD_KEYWORDS.date1);
  d.rawDate2 = valueOf_(answers, FIELD_KEYWORDS.date2);
  d.rawDate3 = valueOf_(answers, FIELD_KEYWORDS.date3);
  d.rawTime  = valueOf_(answers, FIELD_KEYWORDS.time);

  if (!d.name) d.name = 'お申し込みの方';

  // 希望日時のパース（第1希望 → 見つからなければ日付らしい回答を総当たり）
  var parsed = parseDateTime_(d.rawDate, d.rawTime);
  if (!parsed) parsed = parseFromAnyAnswer_(answers, d.rawTime);

  if (parsed) {
    d.startTime = parsed.date;
    d.allDay = !parsed.hasTime;
    d.endTime = new Date(parsed.date.getTime() + CONFIG.SESSION_MINUTES * 60 * 1000);
  }
  return d;
}

function valueOf_(answers, keywords) {
  var key = pickField_(answers, keywords);
  return key ? answers[key] : '';
}

/** 設問タイトルにキーワードを含む最初の項目を返す */
function pickField_(answers, keywords) {
  for (var k = 0; k < keywords.length; k++) {
    var kw = keywords[k].toLowerCase();
    for (var title in answers) {
      if (title.toLowerCase().indexOf(kw) !== -1) return title;
    }
  }
  return '';
}

function findEmailAnywhere_(answers) {
  for (var title in answers) {
    var m = String(answers[title]).match(/[\w.+-]+@[\w-]+\.[\w.-]+/);
    if (m) return m[0];
  }
  return '';
}

function parseFromAnyAnswer_(answers, rawTime) {
  // 日付らしい設問を優先し、電話番号などの誤検出を避ける
  var likely = [], others = [];
  for (var title in answers) {
    if (/日|希望|date|予約|スケジュール/i.test(title)) likely.push(title);
    else others.push(title);
  }
  var order = likely.concat(others);
  for (var i = 0; i < order.length; i++) {
    if (/電話|tel|phone|番号/i.test(order[i])) continue;
    var parsed = parseDateTime_(answers[order[i]], rawTime);
    if (parsed) return parsed;
  }
  return null;
}

// ===================== 日時パース =====================
/**
 * "2026-09-10" / "2026/09/10 14:00" / "9月10日 14時30分" / "9/10 14:00" などに対応。
 * 年がない場合は今年、すでに過ぎている月日なら翌年とみなす。
 */
function parseDateTime_(dateText, timeText) {
  var s = toHalfWidth_(dateText);
  if (!s) return null;

  var now = new Date();
  var y, m, d;

  var full = s.match(/(\d{4})\s*[-\/年.]\s*(\d{1,2})\s*[-\/月.]\s*(\d{1,2})/);
  if (full) {
    y = parseInt(full[1], 10); m = parseInt(full[2], 10); d = parseInt(full[3], 10);
  } else {
    var md = s.match(/(\d{1,2})\s*[\/月.]\s*(\d{1,2})/);
    if (!md) return null;
    m = parseInt(md[1], 10); d = parseInt(md[2], 10);
    y = now.getFullYear();
    var candidate = new Date(y, m - 1, d);
    if (candidate.getTime() < now.getTime() - 24 * 60 * 60 * 1000) y += 1;
  }
  if (m < 1 || m > 12 || d < 1 || d > 31) return null;

  // 時刻は「時刻用の設問」→「日付欄に含まれる時刻」の順で探す
  var hasTime = false, hh = CONFIG.FALLBACK_HOUR, mi = CONFIG.FALLBACK_MINUTE;
  var timeSource = toHalfWidth_(timeText) || stripDatePart_(s, full ? full[0] : null);
  var tm = timeSource.match(/(\d{1,2})\s*[:時]\s*(\d{1,2})?/);
  if (tm) {
    var h = parseInt(tm[1], 10);
    var mnt = tm[2] ? parseInt(tm[2], 10) : 0;
    if (h >= 0 && h <= 23 && mnt >= 0 && mnt <= 59) {
      hh = h; mi = mnt; hasTime = true;
      if (/午後|pm/i.test(timeSource) && hh < 12) hh += 12;
    }
  }

  var result = new Date(y, m - 1, d, hh, mi, 0);
  if (isNaN(result.getTime())) return null;
  return { date: result, hasTime: hasTime };
}

/** 日付部分を取り除いた残りの文字列（時刻の誤検出を防ぐ） */
function stripDatePart_(s, matchedDate) {
  if (matchedDate) return s.replace(matchedDate, ' ');
  return s.replace(/\d{1,2}\s*[\/月.]\s*\d{1,2}\s*日?/, ' ');
}

function toHalfWidth_(text) {
  if (text == null) return '';
  return String(text).replace(/[０-９：／]/g, function (c) {
    return String.fromCharCode(c.charCodeAt(0) - 0xFEE0);
  }).trim();
}

// ===================== カレンダー =====================
function createCalendarEvent_(d) {
  var cal = CalendarApp.getCalendarById(CONFIG.CALENDAR_ID);
  if (!cal) throw new Error('カレンダーが見つかりません: ' + CONFIG.CALENDAR_ID);

  var title = CONFIG.EVENT_PREFIX + (d.allDay ? '【時刻要確認】' : '') + d.name + ' 様';
  if (d.menu) title += '（' + d.menu + '）';

  var description = buildDetailText_(d);
  var options = { description: description };
  if (CONFIG.INVITE_APPLICANT && d.email) {
    options.guests = d.email;
    options.sendInvites = true;
  }
  if (d.method) options.location = d.method;

  var event = d.allDay
    ? cal.createAllDayEvent(title, d.startTime, options)
    : cal.createEvent(title, d.startTime, d.endTime, options);

  if (CONFIG.REMINDER_MINUTES && CONFIG.REMINDER_MINUTES.length) {
    event.removeAllReminders();
    for (var i = 0; i < CONFIG.REMINDER_MINUTES.length; i++) {
      event.addPopupReminder(CONFIG.REMINDER_MINUTES[i]);
    }
  }
  return event;
}

function buildDetailText_(d) {
  var lines = [];
  for (var title in d.answers) {
    lines.push(title + '： ' + d.answers[title]);
  }
  return lines.join('\n');
}

// ===================== メール =====================
function sendAutoReply_(d) {
  var when = d.startTime
    ? formatWhen_(d.startTime, d.allDay)
    : (d.rawDate || '（ご希望日時の記載を確認しております）');

  var subject = '【RAS®】お申し込みありがとうございます（自動返信）';

  var body =
    d.name + ' 様\n\n' +
    'この度は RAS® のセッションにお申し込みいただき、ありがとうございます。\n' +
    '以下の内容で承りました。\n\n' +
    '──────────────────\n' +
    '　ご希望日時： ' + when + '\n' +
    (d.menu   ? '　メニュー　： ' + d.menu + '\n' : '') +
    (d.method ? '　実施方法　： ' + d.method + '\n' : '') +
    (d.rawDate2 ? '　第2希望　： ' + d.rawDate2 + '\n' : '') +
    (d.rawDate3 ? '　第3希望　： ' + d.rawDate3 + '\n' : '') +
    '──────────────────\n\n' +
    'このメールは自動でお送りしています。\n' +
    'ご希望日時での確定可否は、あらためて私からご連絡いたします。\n' +
    '2営業日を過ぎても連絡が届かない場合は、行き違いの可能性がありますので\n' +
    'お手数ですがこのメールにご返信ください。\n\n' +
    '　ご案内までに、ひとつだけ。\n\n' +
    '　セッションでお聞きするのは「あなたは、本当はどうしたいですか」だけです。\n' +
    '　答えを用意しておく必要はありません。\n' +
    '　うまく言葉にできないまま来てくださって大丈夫です。\n\n' +
    '当日お会いできることを楽しみにしております。\n\n' +
    '---------------------------------\n' +
    CONFIG.SENDER_NAME + '\n' +
    '---------------------------------\n';

  var options = { name: CONFIG.SENDER_NAME };
  if (CONFIG.REPLY_TO) options.replyTo = CONFIG.REPLY_TO;

  GmailApp.sendEmail(d.email, subject, body, options);
}

function notifyOwner_(d, event, eventError) {
  if (!CONFIG.OWNER_EMAIL) return;

  var status;
  if (event && !d.allDay)      status = '○ カレンダー登録済み';
  else if (event && d.allDay)  status = '△ 日付のみ登録（時刻が読み取れませんでした）';
  else if (eventError)         status = '× カレンダー登録に失敗： ' + eventError;
  else                         status = '× 希望日時を読み取れませんでした（手動で登録してください）';

  var subject = '【申込】' + d.name + ' 様 / ' +
    (d.startTime ? formatWhen_(d.startTime, d.allDay) : '日時未取得');

  var body =
    status + '\n' +
    '自動返信： ' + (d.email ? '送信済み → ' + d.email : '× 宛先不明のため未送信') + '\n\n' +
    '── 回答内容 ──\n' +
    buildDetailText_(d) + '\n' +
    (event ? '\nカレンダー: ' + event.getTitle() + '\n' : '');

  MailApp.sendEmail(CONFIG.OWNER_EMAIL, subject, body);
}

function formatWhen_(date, allDay) {
  var wd = ['日', '月', '火', '水', '木', '金', '土'];
  var base = Utilities.formatDate(date, CONFIG.TIMEZONE, 'yyyy年M月d日') +
             '(' + wd[date.getDay()] + ')';
  if (allDay) return base + ' ※時刻未定';
  return base + ' ' + Utilities.formatDate(date, CONFIG.TIMEZONE, 'HH:mm') + '〜';
}
