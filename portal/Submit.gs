/**
 * AM5061 — submission links for the portal.
 *
 * WHY THIS REPLACES THE UPLOADER
 * The portal's uploader is gated on Session.getActiveUser().getEmail(). On a
 * personal Google account that returns an EMPTY STRING for every visitor, which
 * is why the Submit tab says "Your account () is not on the roster" — note the
 * empty parentheses. No roster entry can ever match an empty email.
 *
 * Google Forms does not have that problem: a file-upload question forces the
 * respondent to sign in, and the response records the account they used. So
 * the portal hands off to the forms rather than trying to identify anyone.
 *
 * Reads the live published URLs from 06_Submissions/_Forms, so nothing here
 * goes stale if a form is rebuilt.
 */

function getFormLinks_() {
  var cache = CacheService.getScriptCache();
  var hit = cache.get('am5061_formLinks');
  if (hit) { try { return JSON.parse(hit); } catch (e) { /* fall through */ } }

  var out = {};
  try {
    var cIt = DriveApp.getFoldersByName('AM5061 Jul-Nov 2026');
    if (!cIt.hasNext()) return out;
    var sIt = cIt.next().getFoldersByName('06_Submissions');
    if (!sIt.hasNext()) return out;
    var fIt = sIt.next().getFoldersByName('_Forms');
    if (!fIt.hasNext()) return out;

    var files = fIt.next().getFiles();
    while (files.hasNext()) {
      var f = files.next();
      var m = f.getName().match(/AM5061 (D-\d+) submission/);
      if (!m) continue;
      try { out[m[1]] = FormApp.openById(f.getId()).getPublishedUrl(); }
      catch (e) { /* skip a form we cannot open rather than fail the whole page */ }
    }
  } catch (e) { /* portal still renders without the links */ }

  // Six hours. Opening fourteen forms is slow; this keeps the page snappy.
  cache.put('am5061_formLinks', JSON.stringify(out), 21600);
  return out;
}

/** Clear the cache after rebuilding the forms. */
function refreshFormLinks() {
  CacheService.getScriptCache().remove('am5061_formLinks');
  var n = Object.keys(getFormLinks_()).length;
  Logger.log('Cached ' + n + ' form links.');
  return n;
}
