/**
 * RAS®︎ 体験・無料相談 お申し込みフォーム 自動化スクリプト
 *
 *  1. 申込があると、申込者へ自動返信メールを送る
 *  2. 希望日時を読み取り、Googleカレンダーに「仮」の予定を作成する
 *  3. 主催者（AKEMI）に通知メールを送る
 *
 * このフォームの希望日時は自由記述（第3希望まで）のため、
 * 「9月10日 午後」「平日午前中」といった曖昧な回答が前提です。
 * そこで、読み取れた確度に応じて次の3通りでカレンダーに入れます。
 *
 *   時刻まで読めた  → その時刻に【仮】予定
 *   日付だけ読めた  → その日に終日【仮・時刻未定】予定
 *   何も読めない    → 申込日に終日【要日程調整】予定（取りこぼし防止）
 *
 * いずれも「仮」です。日程確定後にご自身で本予定へ直してください。
 * 設置手順は README.md を参照。
 */

// ===================== 設定 =====================
var CONFIG = {
  // 予定を入れるカレンダーID
  CALENDAR_ID: 'xakemix789@gmail.com',

  // 申込通知の宛先（空にすると通知しません）
  OWNER_EMAIL: 'xakemix789@gmail.com',

  // 自動返信メールの差出人名
  SENDER_NAME: 'RAS®︎×東北 AKEMI',

  // 返信先アドレス（空ならスクリプト実行者のアドレス）
  REPLY_TO: 'xakemix789@gmail.com',

  // セッションの所要時間（分）
  SESSION_MINUTES: 90,

  // 「午前」「午後」などの時間帯表現を時刻に割り当てる（24時間表記）
  SLOT_HOURS: { '午前': 10, '朝': 10, '昼': 12, '午後': 14, '夕方': 17, '夕': 17, '夜': 19 },

  // 日付だけ読めたときに使う仮の開始時刻
  FALLBACK_HOUR: 10,
  FALLBACK_MINUTE: 0,

  // 予定に申込者をゲスト追加するか（trueだとGoogleから招待メールが届きます）
  INVITE_APPLICANT: false,

  // 予定のリマインダー（分前）
  REMINDER_MINUTES: [1440, 60],

  // 「要日程調整」予定のリマインダー（分前）
  TODO_REMINDER_MINUTES: [0],

  TIMEZONE: 'Asia/Tokyo'
};

/**
 * 設問の自動判別に使うキーワード。
 * 2026年9月時点の実際の設問名に合わせてあります。
 * フォームの設問名を変えた場合は、ここに1語足すだけで追従できます。
 */
var FIELD_KEYWORDS = {
  email:   ['メールアドレス', 'メール', 'mail'],
  name:    ['お名前', '氏名', 'name'],
  kana:    ['なまえ', 'ふりがな', 'フリガナ', 'カナ'],
  menu:    ['どちらか', 'お選びください', 'メニュー', 'コース', 'セッション内容'],
  agree:   ['同意', 'キャンセルポリシー', '注意事項'],
  method:  ['実施方法', 'オンライン', '形式', '方法', '会場'],
  dates:   ['希望日時', '希望日', '日時', '日程'],
  note:    ['その他', 'お問い合わせ', 'ご質問', 'ご要望', '備考', '相談内容'],
  phone:   ['電話', 'tel', '携帯']
};

// ===================== 初回セットアップ =====================
/**
 * ★ 最初に1回だけ手動で実行してください。
 * ★ 必ず xakemix789@gmail.com でログインした状態で実行すること。
 *   トリガーは実行した人の権限で動くため、そのアカウントのカレンダーに予定が入り、
 *   そのアカウントのGmailから自動返信が送られます。
 */
function setup() {
  var form = FormApp.getActiveForm();

  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === 'onFormSubmit') {
      ScriptApp.deleteTrigger(triggers[i]);   // 二重送信の防止
    }
  }

  ScriptApp.newTrigger('onFormSubmit').forForm(form).onFormSubmit().create();

  var cal = CalendarApp.getCalendarById(CONFIG.CALENDAR_ID);
  Logger.log('セットアップ完了\nフォーム: %s\nカレンダー: %s\n実行アカウント: %s',
    form.getTitle(),
    cal ? cal.getName() : '★取得できません（CALENDAR_IDと共有設定を確認してください）',
    Session.getEffectiveUser().getEmail());
}

/** 設問名と自動判別の結果をログに出す確認用。設置後に一度実行しておくと安心です。 */
function debugFields() {
  var items = FormApp.getActiveForm().getItems();
  var dummy = {}, list = [];
  for (var i = 0; i < items.length; i++) {
    list.push('[' + items[i].getType() + '] ' + items[i].getTitle());
    dummy[items[i].getTitle()] = '';
  }
  var picked = {};
  for (var key in FIELD_KEYWORDS) picked[key] = pickField_(dummy, FIELD_KEYWORDS[key]) || '(該当なし)';
  Logger.log('■ 設問一覧\n' + list.join('\n') + '\n\n■ 自動判別\n' + JSON.stringify(picked, null, 2));
}

/** 日時の読み取りだけを試すテスト用。実際の回答文を貼って確認できます。 */
function debugParse() {
  var samples = [
    '9月10日 午後、9月12日 午前中、平日午前中',
    '第1希望 2026/09/10 14:00\n第2希望 9/12 10:30\n第3希望 いつでも',
    '平日の夜であればいつでも大丈夫です'
  ];
  for (var i = 0; i < samples.length; i++) {
    var c = extractCandidates_(samples[i]);
    var out = [];
    for (var j = 0; j < c.length; j++) {
      out.push(c[j].raw + ' → ' + (c[j].date ? formatWhen_(c[j].date, c[j].precision) : '読み取り不可'));
    }
    Logger.log('【' + samples[i].replace(/\n/g, ' / ') + '】\n' + out.join('\n'));
  }
}

// ===================== メイン処理 =====================
function onFormSubmit(e) {
  try {
    var data = extractData_(collectAnswers_(e), e);

    var event = null, eventError = '';
    try {
      event = createCalendarEvent_(data);
    } catch (err) {
      eventError = String(err);
    }

    if (data.email) sendAutoReply_(data);
    notifyOwner_(data, event, eventError);

  } catch (err) {
    if (CONFIG.OWNER_EMAIL) {
      MailApp.sendEmail(CONFIG.OWNER_EMAIL,
        '【要対応】申込フォームの自動処理でエラー',
        'エラー内容:\n' + err + '\n\n' + (err.stack || '') +
        '\n\n申込データ自体は残っています。フォームの回答を直接ご確認ください。');
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
    var value = responses[i].getResponse();
    if (Object.prototype.toString.call(value) === '[object Array]') value = value.join(' / ');
    map[String(responses[i].getItem().getTitle()).trim()] = value == null ? '' : String(value).trim();
  }
  return map;
}

function extractData_(answers, e) {
  var d = { answers: answers, submittedAt: new Date() };

  d.email = (e && e.response && typeof e.response.getRespondentEmail === 'function')
    ? (e.response.getRespondentEmail() || '') : '';
  if (!d.email) d.email = valueOf_(answers, FIELD_KEYWORDS.email);
  if (!d.email) d.email = findEmailAnywhere_(answers);

  d.name    = valueOf_(answers, FIELD_KEYWORDS.name) || 'お申し込みの方';
  d.kana    = valueOf_(answers, FIELD_KEYWORDS.kana);
  d.menu    = valueOf_(answers, FIELD_KEYWORDS.menu);
  d.method  = valueOf_(answers, FIELD_KEYWORDS.method);
  d.note    = valueOf_(answers, FIELD_KEYWORDS.note);
  d.phone   = valueOf_(answers, FIELD_KEYWORDS.phone);
  d.rawDates = valueOf_(answers, FIELD_KEYWORDS.dates);

  d.candidates = extractCandidates_(d.rawDates);

  // 最も確度の高い候補を「仮予定」に使う（exact > approx > dateonly）
  d.best = null;
  var rank = { exact: 3, approx: 2, dateonly: 1 };
  for (var i = 0; i < d.candidates.length; i++) {
    var c = d.candidates[i];
    if (!c.date) continue;
    if (!d.best || rank[c.precision] > rank[d.best.precision]) d.best = c;
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

// ===================== 希望日時の読み取り =====================
/**
 * 自由記述の希望日時欄を候補ごとに分解して解釈する。
 * 「9月10日 午後、9月12日 午前中、平日午前中」→ 3候補として扱う。
 */
function extractCandidates_(text) {
  if (!text) return [];
  var normalized = toHalfWidth_(text)
    .replace(/第\s*[1-3１-３一二三]\s*希望[：:]?/g, '\n')
    .replace(/[、,;；・]/g, '\n');

  var chunks = normalized.split(/\r?\n/);
  var out = [];
  for (var i = 0; i < chunks.length; i++) {
    var raw = chunks[i].trim();
    if (!raw) continue;
    var parsed = parseDateTime_(raw);
    out.push({
      raw: raw,
      date: parsed ? parsed.date : null,
      precision: parsed ? parsed.precision : 'none'
    });
    if (out.length >= 5) break;
  }
  return out;
}

/**
 * "2026-09-10" / "2026/09/10 14:00" / "9月10日 14時30分" / "9/10 午後" などに対応。
 * 年がない場合は今年。すでに過ぎた月日なら翌年とみなす。
 * 戻り値の precision: exact(時刻あり) / approx(時間帯のみ) / dateonly(日付のみ)
 */
function parseDateTime_(dateText) {
  var s = toHalfWidth_(dateText);
  if (!s) return null;
  if (/電話|tel/i.test(s)) return null;

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
    if (new Date(y, m - 1, d).getTime() < now.getTime() - 24 * 60 * 60 * 1000) y += 1;
  }
  if (m < 1 || m > 12 || d < 1 || d > 31) return null;

  var rest = stripDatePart_(s, full ? full[0] : null);
  var hh = CONFIG.FALLBACK_HOUR, mi = CONFIG.FALLBACK_MINUTE, precision = 'dateonly';

  var tm = rest.match(/(\d{1,2})\s*[:時]\s*(\d{1,2})?/);
  if (tm) {
    var h = parseInt(tm[1], 10);
    var mnt = tm[2] ? parseInt(tm[2], 10) : 0;
    if (h >= 0 && h <= 23 && mnt >= 0 && mnt <= 59) {
      hh = h; mi = mnt; precision = 'exact';
      if (/午後|pm/i.test(rest) && hh < 12) hh += 12;
    }
  }
  if (precision === 'dateonly') {
    for (var word in CONFIG.SLOT_HOURS) {
      if (rest.indexOf(word) !== -1) {
        hh = CONFIG.SLOT_HOURS[word]; mi = 0; precision = 'approx';
        break;
      }
    }
  }

  var result = new Date(y, m - 1, d, hh, mi, 0);
  if (isNaN(result.getTime())) return null;
  return { date: result, precision: precision };
}

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

  var who = d.name + ' 様';
  var menu = d.menu ? '（' + d.menu + '）' : '';
  var description = buildDetailText_(d);
  var options = { description: description };
  if (d.method) options.location = d.method;
  if (CONFIG.INVITE_APPLICANT && d.email) { options.guests = d.email; options.sendInvites = true; }

  var event, reminders = CONFIG.REMINDER_MINUTES;

  if (d.best && d.best.precision === 'dateonly') {
    event = cal.createAllDayEvent('【仮・時刻未定】' + who + menu, d.best.date, options);

  } else if (d.best) {
    var end = new Date(d.best.date.getTime() + CONFIG.SESSION_MINUTES * 60 * 1000);
    var prefix = d.best.precision === 'exact' ? '【仮】' : '【仮・時間帯のみ】';
    event = cal.createEvent(prefix + who + menu, d.best.date, end, options);

  } else {
    // 日時が読み取れないケース。取りこぼさないよう申込日に「やること」を置く
    event = cal.createAllDayEvent('【要日程調整】' + who + menu, d.submittedAt, options);
    reminders = CONFIG.TODO_REMINDER_MINUTES;
  }

  if (reminders && reminders.length) {
    event.removeAllReminders();
    for (var i = 0; i < reminders.length; i++) event.addPopupReminder(reminders[i]);
  }
  return event;
}

function buildDetailText_(d) {
  var lines = ['■ 読み取った希望日時'];
  if (d.candidates.length) {
    for (var i = 0; i < d.candidates.length; i++) {
      var c = d.candidates[i];
      lines.push('　' + (i + 1) + '. ' + c.raw +
        (c.date ? '　→ ' + formatWhen_(c.date, c.precision) : '　→ 読み取り不可'));
    }
  } else {
    lines.push('　（記載なし）');
  }
  lines.push('', '※ この予定は仮です。日程確定後に修正してください。', '', '■ 回答内容');
  for (var title in d.answers) lines.push('　' + title + '： ' + d.answers[title]);
  return lines.join('\n');
}

// ===================== メール =====================
function sendAutoReply_(d) {
  var subject = '【RAS®︎×東北】お申し込みを受け付けました（自動返信）';

  var wishes = '';
  if (d.candidates.length) {
    for (var i = 0; i < d.candidates.length; i++) {
      wishes += '　　第' + (i + 1) + '希望： ' + d.candidates[i].raw + '\n';
    }
  } else if (d.rawDates) {
    wishes = '　　' + d.rawDates + '\n';
  }

  var body =
    d.name + ' 様\n\n' +
    'この度は RAS®︎ 体験・無料相談にお申し込みいただき、ありがとうございます。\n' +
    '以下の内容で受付を完了しました。\n\n' +
    '──────────────────────────\n' +
    (d.menu   ? '　ご希望　　： ' + d.menu + '\n' : '') +
    (d.method ? '　実施方法　： ' + d.method + '\n' : '') +
    (wishes   ? '　ご希望日時\n' + wishes : '') +
    '──────────────────────────\n\n' +
    'このメールは自動でお送りしています。\n' +
    '日程の確定は、48時間以内にあらためて私からご連絡いたします。\n' +
    '48時間を過ぎても届かない場合は、迷惑メールフォルダをご確認のうえ、\n' +
    'お手数ですがこのメールにご返信ください。\n\n' +
    'キャンセルの場合は、前日までにご連絡をお願いいたします。\n\n' +
    '　──　当日までに、ひとつだけ　──\n\n' +
    '　RAS®︎でお聞きするのは「あなたは、本当はどうしたいですか」だけです。\n' +
    '　答えを用意しておく必要はありません。\n' +
    '　うまく言葉にできないまま来てくださって大丈夫です。\n\n' +
    'お会いできることを楽しみにしております。\n\n' +
    '────────────────────\n' +
    'RAS®︎×東北\n' +
    'RAS®︎認定ファシリテーター AKEMI\n' +
    '電話　090-4636-0195\n' +
    'メール　xakemix789@gmail.com\n' +
    '対面セッション：宮城県大郷町\n' +
    '────────────────────\n';

  var options = { name: CONFIG.SENDER_NAME };
  if (CONFIG.REPLY_TO) options.replyTo = CONFIG.REPLY_TO;
  GmailApp.sendEmail(d.email, subject, body, options);
}

function notifyOwner_(d, event, eventError) {
  if (!CONFIG.OWNER_EMAIL) return;

  var status;
  if (eventError)                            status = '× カレンダー登録に失敗： ' + eventError;
  else if (!d.best)                          status = '△ 希望日時を読み取れず、申込日に【要日程調整】を作成';
  else if (d.best.precision === 'exact')     status = '○ 仮予定を登録： ' + formatWhen_(d.best.date, 'exact');
  else if (d.best.precision === 'approx')    status = '○ 仮予定を登録（時間帯のみ）： ' + formatWhen_(d.best.date, 'approx');
  else                                       status = '△ 日付のみ登録： ' + formatWhen_(d.best.date, 'dateonly');

  var subject = '【申込】' + d.name + ' 様' + (d.menu ? ' / ' + d.menu : '');
  var body = status + '\n' +
    '自動返信： ' + (d.email ? '送信済み → ' + d.email : '× 宛先不明のため未送信') + '\n\n' +
    buildDetailText_(d) + '\n';

  MailApp.sendEmail(CONFIG.OWNER_EMAIL, subject, body);
}

function formatWhen_(date, precision) {
  var wd = ['日', '月', '火', '水', '木', '金', '土'];
  var base = Utilities.formatDate(date, CONFIG.TIMEZONE, 'yyyy年M月d日') + '(' + wd[date.getDay()] + ')';
  if (precision === 'dateonly') return base + ' ※時刻未定';
  var hm = Utilities.formatDate(date, CONFIG.TIMEZONE, 'HH:mm');
  return base + ' ' + hm + (precision === 'approx' ? '頃〜（時間帯のみ）' : '〜');
}
