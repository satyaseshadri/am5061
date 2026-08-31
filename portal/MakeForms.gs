/**
 * AM5061 — submission forms, without the portal.
 *
 * WHY FORMS AND NOT THE PORTAL
 * The Apps Script portal identifies students with
 * Session.getActiveUser().getEmail(). On a PERSONAL Google account that returns
 * an empty string for anyone outside the owner's domain, so the roster never
 * matches. A Forms FILE UPLOAD question requires the respondent to sign in and
 * records the account they used, so it works where the portal cannot.
 *
 * WHY A TEMPLATE
 * Apps Script CANNOT create a file-upload question. There is no
 * addFileUploadItem(). FileUploadItem exists only for reading a form that
 * already has one. So you build ONE form by hand, and this script clones it
 * fourteen times — a copy preserves the upload question.
 *
 * ── STEP 1, ONCE, BY HAND ─────────────────────────────────────────────
 * 1. forms.google.com → Blank form
 * 2. Title it exactly:   AM5061 Submission TEMPLATE
 * 3. Settings (gear) → Responses → turn ON "Collect email addresses"
 *                                  (choose Verified if offered)
 * 4. Add three questions, in this order:
 *      Q1  Short answer   "Roll number"            → Required
 *      Q2  File upload    "Your files"             → Required
 *            • allow up to 5 files, 100 MB each
 *            • accept any file type
 *      Q3  Paragraph      "Assumptions and sources" → not required
 * 5. Close the form. Leave it in My Drive; the script will find it by name.
 *
 * ── STEP 2 ────────────────────────────────────────────────────────────
 * Select makeAllForms → Run. Links print in the Execution log.
 * Re-running is safe: it skips deliverables whose form already exists.
 */

var COURSE_FOLDER   = 'AM5061 Jul-Nov 2026';
var TEMPLATE_NAME   = 'AM5061 Submission TEMPLATE';
var FORMS_SUBFOLDER = '06_Submissions';
var RESPONSES_NAME  = 'AM5061 Submissions (Forms)';

var DELIVERABLES = [
  ['D-1',  1, 'The 28 kW dairy pasteurisation heat pump'],
  ['D-2',  2, 'Chilled-water distribution, 500 TR campus plant'],
  ['D-3',  3, 'Cooling tower + evaporative pre-cooler, Chennai'],
  ['D-4',  4, 'Steam header insulation, Tiruppur textile mill'],
  ['D-5',  5, 'Waterwall tube, 20 TPH bagasse-fired boiler'],
  ['D-6',  6, 'Condenser of a 10 kW residential heat pump'],
  ['D-7',  7, 'Liquid cooling for a 50 kW GPU rack'],
  ['D-8',  8, 'Waste-heat recovery boiler on a cement kiln'],
  ['D-9',  9, 'Shell-and-tube condenser: mechanical design'],
  ['D-10', 10, 'Bagasse cogeneration, 3500 TCD sugar mill'],
  ['D-11', 11, 'Transcritical CO2 booster, supermarket cold chain'],
  ['D-12', 12, 'Solar LiBr-water absorption chiller, 500 t store'],
  ['D-13', 13, 'ORC on cement kiln waste heat'],
  ['D-14', 14, 'Plant-level audit: Sankey, exergy, cost, carbon']
];

function _courseFolder_() {
  var it = DriveApp.getFoldersByName(COURSE_FOLDER);
  if (!it.hasNext()) throw new Error('Course folder not found: ' + COURSE_FOLDER);
  return it.next();
}

function _childFolder_(parent, name) {
  var it = parent.getFoldersByName(name);
  return it.hasNext() ? it.next() : parent.createFolder(name);
}

function _template_() {
  var it = DriveApp.getFilesByName(TEMPLATE_NAME);
  if (!it.hasNext()) {
    throw new Error(
      'Template not found. Create a form called exactly "' + TEMPLATE_NAME +
      '" with a Roll number question, a FILE UPLOAD question and a paragraph ' +
      'question, then run this again. See the header of this file for the steps.');
  }
  return it.next();
}

/** Confirms the template is usable BEFORE creating fourteen copies of a mistake. */
function checkTemplate() {
  var f = FormApp.openById(_template_().getId());
  var items = f.getItems();
  var kinds = items.map(function (i) { return i.getType().toString(); });
  var hasUpload = kinds.indexOf('FILE_UPLOAD') !== -1;
  Logger.log('Template: "' + f.getTitle() + '"');
  Logger.log('Questions: ' + kinds.join(', '));
  Logger.log('Collects email: ' + f.collectsEmail());
  Logger.log(hasUpload
    ? 'FILE UPLOAD present. Good — run makeAllForms.'
    : 'NO FILE UPLOAD QUESTION. Add one in the Forms editor before continuing.');
  return hasUpload;
}

function makeAllForms() {
  var course      = _courseFolder_();
  var subs        = _childFolder_(course, FORMS_SUBFOLDER);
  var formsFolder = _childFolder_(subs, '_Forms');
  var admin       = _childFolder_(course, '00_Admin');
  var tmplFile    = _template_();

  if (!checkTemplate()) {
    throw new Error('Template has no file-upload question. Add one, then re-run.');
  }

  // one spreadsheet, one tab per deliverable
  var ss, ssIt = admin.getFilesByName(RESPONSES_NAME);
  if (ssIt.hasNext()) {
    ss = SpreadsheetApp.open(ssIt.next());
  } else {
    ss = SpreadsheetApp.create(RESPONSES_NAME);
    var sf = DriveApp.getFileById(ss.getId());
    admin.addFile(sf);
    DriveApp.getRootFolder().removeFile(sf);
  }

  var lines = [];
  DELIVERABLES.forEach(function (d) {
    var code = d[0], week = d[1], title = d[2];
    var name = 'AM5061 ' + code + ' submission';

    var existing = formsFolder.getFilesByName(name);
    if (existing.hasNext()) {
      lines.push(code + '  (already existed)  ' +
                 FormApp.openById(existing.next().getId()).getPublishedUrl());
      return;
    }

    // A COPY keeps the file-upload question that Apps Script cannot create.
    var copy = tmplFile.makeCopy(name, formsFolder);
    var form = FormApp.openById(copy.getId());

    form.setTitle('AM5061 · ' + code + ' — Week ' + week)
        .setDescription(title + '\n\n' +
          'Sign in with your IIT Madras Google account. Upload your workbook ' +
          'and any supporting files. You may submit more than once; the latest ' +
          'submission is the one marked.')
        .setAllowResponseEdits(true)
        .setProgressBar(false);

    form.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());
    lines.push(code + '  ' + form.getPublishedUrl());
  });

  Logger.log('\n=== AM5061 submission form links ===\n' + lines.join('\n') +
             '\n\nResponses: ' + ss.getUrl() +
             '\nForms:     ' + formsFolder.getUrl() +
             '\n\nNEXT: set a closing date per form, or run closeForm("D-1").');
  return lines;
}

/** Stop accepting responses for one deliverable. */
function closeForm(code) {
  var formsFolder = _childFolder_(_childFolder_(_courseFolder_(), FORMS_SUBFOLDER), '_Forms');
  var it = formsFolder.getFilesByName('AM5061 ' + code + ' submission');
  if (!it.hasNext()) throw new Error('No form for ' + code);
  FormApp.openById(it.next().getId())
    .setAcceptingResponses(false)
    .setCustomClosedFormMessage('AM5061 ' + code + ' is closed. Contact the ' +
      'instructor if you need a late submission considered.');
  Logger.log(code + ' closed.');
}

/** Roll numbers with no submission, using the Roster tab of the Control Sheet. */
function whoIsMissing(code) {
  var admin = _childFolder_(_courseFolder_(), '00_Admin');
  var ssIt = admin.getFilesByName(RESPONSES_NAME);
  if (!ssIt.hasNext()) throw new Error('Responses spreadsheet not found');

  var submitted = {};
  SpreadsheetApp.open(ssIt.next()).getSheets().forEach(function (sh) {
    if (sh.getName().indexOf(code) === -1) return;
    var v = sh.getDataRange().getValues();
    for (var i = 1; i < v.length; i++) {
      for (var c = 0; c < v[i].length; c++) {
        var cell = String(v[i][c] || '').trim().toUpperCase();
        if (/^[A-Z]{2}\d{2}[A-Z]\d{3}$/.test(cell)) { submitted[cell] = true; break; }
      }
    }
  });

  var ctrl = admin.getFilesByName('AM5061 Control Sheet');
  if (!ctrl.hasNext()) {
    Logger.log('Submitted for ' + code + ': ' + Object.keys(submitted).join(', '));
    return;
  }
  var roster = SpreadsheetApp.open(ctrl.next()).getSheetByName('Roster');
  if (!roster) { Logger.log('No Roster tab.'); return; }
  var rows = roster.getDataRange().getValues(), missing = [];
  for (var j = 1; j < rows.length; j++) {
    var r = String(rows[j][1] || '').trim().toUpperCase();
    var active = String(rows[j][5] || '').trim().toUpperCase();
    if (r && active !== 'NO' && !submitted[r]) missing.push(r);
  }
  Logger.log(code + ': ' + Object.keys(submitted).length + ' submitted, ' +
             missing.length + ' missing -> ' + missing.join(', '));
}
