# Patch: make Submit work on a personal Google account

## The problem you are seeing

> Your account **()** is not on the roster, so you cannot submit yet.

Those empty parentheses are the whole story. `Session.getActiveUser().getEmail()`
returned an **empty string**, so no roster row could ever match. On a personal
Google account that call returns empty for every visitor — including you. It is
a documented Apps Script privacy restriction, not a bug in the portal.

Everything that does **not** need identity already works: Today, Weeks & Cases,
Schedule, Software, Term Projects. Only **Submit** and **My Progress** are broken.

This patch hands submission over to the Google Forms, which identify students
properly because a file-upload question forces a Google sign-in.

---

## Edit 1 — add a SERVER file

Files → **+** → **Script** → name it **`FormLinks`**. Paste in `FormLinks.gs`
from this folder.

> **This file holds server code only.** It must contain nothing but
> `getFormLinks_()` and `refreshFormLinks()`. If you paste the browser code from
> Edit 3 in here you get `ReferenceError: B is not defined` — `B` is a
> client-side variable that only exists inside `Portal_v2.html`.

## Edit 2 — Code.gs, one line

Find this, around **line 60**:

```javascript
    weeks: buildWeekPayload_(),
```

Add one line immediately above it:

```javascript
    formLinks: getFormLinks_(),
    weeks: buildWeekPayload_(),
```

## Edit 3 — Portal_v2.html, replace the Submit block

> **This goes in `Portal_v2.html`, NOT in a `.gs` file.** It runs in the
> student's browser and uses `B`, the payload the server sends to the page.

Find the block starting at about **line 340**:

```javascript
/* ---------------- SUBMIT ---------------- */
```

Replace **everything** from that comment down to (and including) the closing
`})();` of that section — it ends just before `/* ---------------- MY PROGRESS`
— with this:

```javascript
/* ---------------- SUBMIT ---------------- */
(function(){
  var L = B.formLinks || {};
  var codes = Object.keys(L).sort(function(a,b){
    return parseInt(a.slice(2),10) - parseInt(b.slice(2),10);
  });

  if (!codes.length) {
    $('#t-submit').innerHTML = '<div class="card"><h2>Submission</h2>' +
      '<p class="sub">Submission forms are not set up yet. ' +
      'Email the instructor.</p></div>';
    return;
  }

  var h = '<div class="card"><h2>Submit a deliverable</h2>' +
    '<p class="sub">Each deliverable has its own upload form. ' +
    '<b>Sign in with your IIT Madras Google account</b> so your submission is ' +
    'recorded against you. Re-submitting is fine — the latest version is the ' +
    'one marked.</p><div class="grid">';

  codes.forEach(function(c){
    var wk = c.slice(2);
    h += '<div class="row"><div><b>' + esc(c) + '</b> ' +
         '<span class="sub">Week ' + esc(wk) + '</span></div>' +
         '<a class="go" target="_blank" rel="noopener" href="' + esc(L[c]) + '">Open form</a></div>';
  });

  h += '</div></div>';
  $('#t-submit').innerHTML = h;
})();
```

## Edit 4 — Portal_v2.html, the My Progress guard

Find, around **line 410**:

```javascript
  if (!B.user.known) {
    $('#t-me').innerHTML = '<div class="card"><h2>My progress</h2>' +
      '<p class="sub">Not on the roster — nothing to show.</p></div>'; return;
  }
```

Replace with:

```javascript
  if (!B.user.known) {
    $('#t-me').innerHTML = '<div class="card"><h2>My progress</h2>' +
      '<p class="sub">Marks and attendance cannot be shown here. This portal ' +
      'runs on a personal Google account, which cannot verify who you are, and ' +
      'showing marks to an unverified visitor would expose other students’ ' +
      'data. Ask the instructor for your standing.</p></div>'; return;
  }
```

> **Do not** be tempted to let students type a roll number to see their marks.
> Without verified identity anyone could enter any roll number and read someone
> else's grades.

---

## Then

**Deploy → Manage deployments → edit (pencil) → Version: New version → Deploy.**
Editing files alone does not update a live web app.

Reload the portal. Submit should now list the deliverables with an **Open form**
button each.

## After rebuilding forms

Run `refreshFormLinks` once. The links are cached for six hours.

## The permanent fix

All of this is a workaround for the account type. Move the course to an IIT
Madras Workspace account and the original portal works as written: real
identity, in-portal uploads, per-student marks and attendance, and domain-only
access. This patch keeps you running until then.
