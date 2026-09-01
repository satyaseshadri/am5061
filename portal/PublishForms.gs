/**
 * AM5061 — publish the submission forms.
 *
 * WHY THIS IS NEEDED
 * Google moved Forms to an explicit "publish" model. A form created by COPYING
 * another — which is how makeAllForms builds all fourteen — arrives UNPUBLISHED.
 * Opening its link then gives:
 *
 *     "We're sorry. This document is not published."
 *
 * setAcceptingResponses(true) is the long-standing switch. Newer accounts also
 * have setPublished(true). Which one exists depends on your account, so this
 * feature-detects rather than assuming, and reports exactly what it found.
 *
 * Run publishAllForms, then checkFormsLive.
 */

function _formsFolder_() {
  var c = DriveApp.getFoldersByName('AM5061 Jul-Nov 2026');
  if (!c.hasNext()) throw new Error('Course folder not found');
  var s = c.next().getFoldersByName('06_Submissions');
  if (!s.hasNext()) throw new Error('06_Submissions not found');
  var f = s.next().getFoldersByName('_Forms');
  if (!f.hasNext()) throw new Error('_Forms not found — run makeAllForms first');
  return f.next();
}

function publishAllForms() {
  var files = _formsFolder_().getFiles();
  var done = [], notes = [];

  while (files.hasNext()) {
    var file = files.next();
    if (!/AM5061 D-\d+ submission/.test(file.getName())) continue;
    var form = FormApp.openById(file.getId());
    var what = [];

    try { form.setAcceptingResponses(true); what.push('accepting'); }
    catch (e) { notes.push(file.getName() + ': setAcceptingResponses -> ' + e.message); }

    // Only on accounts that have the newer publishing model.
    if (typeof form.setPublished === 'function') {
      try { form.setPublished(true); what.push('published'); }
      catch (e) { notes.push(file.getName() + ': setPublished -> ' + e.message); }
    }

    done.push(file.getName().replace('AM5061 ', '').replace(' submission', '') +
              ' [' + what.join(', ') + ']');
  }

  Logger.log('Processed ' + done.length + ' forms:\n  ' + done.join('\n  '));
  if (!done.length) Logger.log('No forms matched. Did makeAllForms run?');
  if (notes.length) Logger.log('\nProblems:\n  ' + notes.join('\n  '));
  Logger.log('\nsetPublished available on this account: ' +
             (typeof FormApp.openById(_formsFolder_().getFiles().next().getId()).setPublished
              === 'function'));
  return done.length;
}

/** Report the live state and the URL of every form. Open one to confirm. */
function checkFormsLive() {
  var files = _formsFolder_().getFiles();
  var rows = [];
  while (files.hasNext()) {
    var file = files.next();
    if (!/AM5061 D-\d+ submission/.test(file.getName())) continue;
    var form = FormApp.openById(file.getId());
    var pub = (typeof form.isPublished === 'function') ? form.isPublished() : 'n/a';
    rows.push({
      code: (file.getName().match(/D-\d+/) || ['?'])[0],
      accepting: form.isAcceptingResponses(),
      published: pub,
      url: form.getPublishedUrl()
    });
  }
  rows.sort(function (a, b) {
    return parseInt(a.code.slice(2), 10) - parseInt(b.code.slice(2), 10);
  });
  rows.forEach(function (r) {
    Logger.log(r.code + '  accepting=' + r.accepting + '  published=' + r.published +
               '\n    ' + r.url);
  });
  var bad = rows.filter(function (r) { return !r.accepting; }).length;
  Logger.log('\n' + rows.length + ' forms, ' + bad + ' not accepting responses.');
  return rows;
}
