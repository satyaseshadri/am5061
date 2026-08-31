/**
 * AM5061 — submission forms, without the portal.
 *
 * WHY THIS EXISTS
 * The Apps Script portal identifies students with
 * Session.getActiveUser().getEmail(). On a PERSONAL Google account that call
 * returns an empty string for anyone outside the owner's domain, so the roster
 * never matches and submissions cannot be attributed. That is a documented
 * Apps Script privacy restriction, not a bug in Code.gs.
 *
 * Google Forms does not have that problem. A file-upload question REQUIRES the
 * respondent to sign in to Google, and the response records the account they
 * signed in with. So this works today, on the account the course already lives
 * on, with no migration.
 *
 * WHAT YOU GET
 *   - one form per deliverable, D-1 to D-14
 *   - uploads land in YOUR Drive; students cannot see each other's work
 *   - one responses spreadsheet in 00_Admin, one tab per deliverable
 *   - a printed list of form links to paste into the course index
 *
 * HOW TO RUN
 *   1. script.google.com -> your AM5061 Portal project (or a new one)
 *   2. Files -> + -> Script -> name it MakeForms -> paste this in
 *   3. Select makeAllForms in the dropdown -> Run -> authorise
 *   4. Copy the links from the execution log
 *
 * Re-running is safe: it skips any deliverable whose form already exists.
 */

var COURSE_FOLDER = 'AM5061 Jul-Nov 2026';
var FORMS_SUBFOLDER = '06_Submissions';

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

function makeAllForms() {
  var course = _courseFolder_();
  var subs   = _childFolder_(course, FORMS_SUBFOLDER);
  var formsFolder = _childFolder_(subs, '_Forms');

  // one spreadsheet collects every deliverable, one tab each
  var ssName = 'AM5061 Submissions (Forms)';
  var ssIt = _childFolder_(course, '00_Admin').getFilesByName(ssName);
  var ss;
  if (ssIt.hasNext()) {
    ss = SpreadsheetApp.open(ssIt.next());
  } else {
    ss = SpreadsheetApp.create(ssName);
    var f = DriveApp.getFileById(ss.getId());
    _childFolder_(course, '00_Admin').addFile(f);
    DriveApp.getRootFolder().removeFile(f);
  }

  var lines = [];
  DELIVERABLES.forEach(function (d) {
    var code = d[0], week = d[1], title = d[2];
    var formName = 'AM5061 ' + code + ' submission';

    var existing = formsFolder.getFilesByName(formName);
    if (existing.hasNext()) {
      var ef = FormApp.openById(existing.next().getId());
      lines.push(code + '  (already existed)  ' + ef.getPublishedUrl());
      return;
    }

    var form = FormApp.create(formName);
    form.setTitle('AM5061 · ' + code + ' — Week ' + week)
        .setDescription(title + '\n\n' +
          'Sign in with your IIT Madras Google account. ' +
          'Upload your workbook and any supporting files. ' +
          'You may submit more than once; the latest submission is the one marked.')
        .setCollectEmail(true)
        .setAllowResponseEdits(true)
        .setLimitOneResponsePerUser(false)
        .setProgressBar(false);

    form.addTextItem()
        .setTitle('Roll number')
        .setHelpText('Exactly as on your ID card, e.g. AM25M017')
        .setRequired(true);

    // File upload FORCES Google sign-in. That is what makes this work on a
    // personal account where the portal's identity call does not.
    form.addFileUploadItem()
        .setTitle(code + ' — your files')
        .setHelpText('The Excel workbook is required. Add your notebook or a ' +
                     'PDF report if the brief asks for one.')
        .setNumberOfFiles(5)
        .setMaxFileSize(100 * 1024 * 1024)   // 100 MB each
        .setRequired(true);

    form.addParagraphTextItem()
        .setTitle('Assumptions and sources')
        .setHelpText('Anything the marker needs to know: property source, ' +
                     'assumed values, correlations used and where they came from.')
        .setRequired(false);

    form.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());

    // file it away so the course folder stays tidy
    var file = DriveApp.getFileById(form.getId());
    formsFolder.addFile(file);
    DriveApp.getRootFolder().removeFile(file);

    lines.push(code + '  ' + form.getPublishedUrl());
  });

  Logger.log('\n=== AM5061 submission form links ===\n' + lines.join('\n') +
             '\n\nResponses: ' + ss.getUrl() +
             '\nUploads:   ' + subs.getUrl() +
             '\n\nNEXT: set a closing date on each form (Settings -> Presentation)' +
             '\n      or run closeForm("D-1") after the deadline.');
  return lines;
}

/** Close one deliverable after its deadline. */
function closeForm(code) {
  var course = _courseFolder_();
  var formsFolder = _childFolder_(_childFolder_(course, FORMS_SUBFOLDER), '_Forms');
  var it = formsFolder.getFilesByName('AM5061 ' + code + ' submission');
  if (!it.hasNext()) throw new Error('No form for ' + code);
  var form = FormApp.openById(it.next().getId());
  form.setAcceptingResponses(false)
      .setCustomClosedFormMessage('AM5061 ' + code + ' is closed. ' +
        'Contact the instructor if you need a late submission considered.');
  Logger.log(code + ' closed.');
}

/** Who has not submitted a given deliverable. Reads the Roster tab if present. */
function whoIsMissing(code) {
  var course = _courseFolder_();
  var ssIt = _childFolder_(course, '00_Admin')
               .getFilesByName('AM5061 Submissions (Forms)');
  if (!ssIt.hasNext()) throw new Error('Responses spreadsheet not found');
  var ss = SpreadsheetApp.open(ssIt.next());

  var submitted = {};
  ss.getSheets().forEach(function (sh) {
    if (sh.getName().indexOf(code) === -1) return;
    var v = sh.getDataRange().getValues();
    for (var i = 1; i < v.length; i++) {
      var roll = String(v[i][2] || '').trim().toUpperCase();
      if (roll) submitted[roll] = true;
    }
  });

  var ctrl = _childFolder_(course, '00_Admin').getFilesByName('AM5061 Control Sheet');
  if (!ctrl.hasNext()) {
    Logger.log('Submitted for ' + code + ': ' + Object.keys(submitted).join(', '));
    return;
  }
  var roster = SpreadsheetApp.open(ctrl.next()).getSheetByName('Roster');
  if (!roster) { Logger.log('No Roster tab.'); return; }
  var rows = roster.getDataRange().getValues();
  var missing = [];
  for (var j = 1; j < rows.length; j++) {
    var r = String(rows[j][1] || '').trim().toUpperCase();
    var active = String(rows[j][5] || '').trim().toUpperCase();
    if (r && active !== 'NO' && !submitted[r]) missing.push(r);
  }
  Logger.log(code + ': ' + Object.keys(submitted).length + ' submitted, ' +
             missing.length + ' missing -> ' + missing.join(', '));
}
