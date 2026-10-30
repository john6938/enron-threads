var qs = querystring.parse();
var defaults = {
    data: 'data/',
    layout: 'd3v4force',
    tdur: 1000,
    r: 2,
    top: 5,
    nppl: 6,
    minhops: 3,
    user: '',
    thread: ''
};
var options = Object.assign(Object.assign({}, defaults), qs);

function replace_query_string() {
    // i'm not sure why i'm not using sync-url-options.js
    var m = {};
    Object.keys(defaults).forEach(function(k) {
        if(defaults[k] != options[k]) // intentionally coercive inequality
            m[k] = options[k];
    });
    window.history.replaceState('enron-threads', null, window.location.origin + window.location.pathname +
                                '?' + decodeURIComponent(querystring.generate(m)));
}

function random_item(array) {
    return array[Math.floor(Math.random() * array.length)];
}

function radius(adjacent, followed, k, r, set) {
    console.assert(set.has(k));
    console.assert(k && k !== 'undefined');
    if(!r)
        return {nodes: [k], edges: []};
    // only include emails in the top x%; don't follow an edge twice
    var adjs = Object.keys(adjacent[k]).filter(
        j => set.has(j) && (!followed[j] || !followed[j][k]));
    followed[k] = {};
    var edges = adjs.map(a => (followed[k][a] = {source: k, target: a, type: 'proximity'}));
    var crad = adjs.map(k2 => radius(adjacent, followed, k2, r-1, set));
    return {
        nodes: Array.prototype.concat.apply([k], crad.map(c => c.nodes)),
        edges: Array.prototype.concat.apply(edges, crad.map(c => c.edges))
    };
}

function thread_opacity(v) {
    return e => e.value.type === 'thread' ? v : 1;
}

var starts = [], finishes = [], newThreads = [];
var rendered = false;
var diagram = dc_graph.diagram('#graph')
    .layoutEngine(dc_graph.spawn_engine(options.layout)
                  .angleForce(.1)
                  .initialCharge(-200)
                  .chargeForce(-200)
                  .collisionRadius(15)
                  .gravityStrength(0))
    .edgeSource(function(e) { return e.value.source; })
    .edgeTarget(function(e) { return e.value.target; })
    .layoutUnchanged(true) // dc-js/dc.graph.js#79
    .transitionDuration(+options.tdur)
    .autoZoom('always')
    .zoomExtent([0.1, 5])
    .zoomDuration(1000)
    .nodeRadius(7)
    .nodeLabel(function(n) {
        var label = '';
        if(starts.includes(n.key))
            label += 'S';
        if(finishes.includes(n.key))
            label += 'F';
        return label;
    })
    .edgeLabel(function(e) {
        var n = e.value.forward + e.value.backward;
        return n > 1 ? n : null;
    })
    .edgeArrowhead(e => e.value.forward ? 'vee' : null)
    .edgeArrowtail(e => e.value.backward ? 'vee' : null)
    .edgeStroke(e => e.value.type === 'thread' ? 'green' : 'black')
    .edgeStrokeWidth(e => e.value.type === 'thread' ? 3 : 1)
    .edgeOpacity(thread_opacity(0.7))
    .edgeSort(e => e.value.type) // alphabetic order!
;

diagram.on('drawn', attach_graph_click_handlers);
diagram.on('end', attach_graph_click_handlers);

var highlighter = dc_graph.highlight_neighbors({edgeStroke: 'darkorange'});
diagram.child('highlight-neighbors', highlighter);

var reader = dc_graph.path_reader()
    .elementList(thread => thread.hops)
    .elementType('node') // we have no edges, they are unused anyway
    .nodeKey(hop => hop.from)
    .pathStrength(p => newThreads.includes(p) ? 0 : 1);
var spliner = dc_graph.draw_spline_paths(
    reader,
    {edgeStroke: '#08a', edgeStrokeWidth: 3, edgeOpacity: 0.7},
    {edgeStroke: '#0ad', edgeOpacity: 1},
    {edgeStroke: '#f94'})
    .selectedStrength(5);
diagram.child('spliner', spliner);

function highlight_email_by_sender(senderKey) {
    var key = senderKey.toLowerCase();
    var firstMatch = null;
    d3.select('#email-panel').selectAll('.email-message')
        .classed('highlighted', function() {
            var from = (d3.select(this).attr('data-from') || '').toLowerCase();
            var match = from.indexOf(key) !== -1;
            if(match && !firstMatch) firstMatch = this;
            return match;
        });
    if(firstMatch) firstMatch.scrollIntoView({behavior: 'smooth', block: 'nearest'});
}

function attach_graph_click_handlers() {
    d3.select('#graph').selectAll('g.node').on('click.highlight', function(d) {
        var key = d && ((d.orig && d.orig.key) || d.cola && d.cola.dcg_nodeKey);
        if(key) highlight_email_by_sender(key);
    });
    d3.select('#graph').selectAll('path.edge-hover,path.edge').on('click.highlight', function(d) {
        var ev = d && d.orig && d.orig.value;
        if(ev) {
            var sender = (ev.forward || 0) >= (ev.backward || 0)
                ? ev.target : ev.source;
            highlight_email_by_sender(sender);
        }
    });
}

// email-content cache keyed by username
var emailContentCache = {};

function usernameFromFile(filepath) {
    var parts = filepath.split('/');
    var idx = parts.indexOf('maildir');
    if(idx !== -1 && idx + 1 < parts.length)
        return parts[idx + 1];
    return parts.length >= 2 ? parts[parts.length - 2] : null;
}

function show_email_content(thread, dataPath) {
    var filepath = thread.file;
    var username = usernameFromFile(filepath);
    var panel = d3.select('#email-panel');
    if(!username) { panel.html('<em>Cannot determine user.</em>'); return; }

    var threadLabel = filepath.split('/').slice(-2).join('/');

    function render(emails) {
        panel.html('');
        panel.append('div').attr('class', 'email-panel-thread').text(threadLabel);
        if(!emails || !emails.length) {
            panel.append('p').attr('class', 'email-unavailable').text('No content available.');
            return;
        }
        emails.forEach(function(email) {
            var msg = panel.append('div').attr('class', 'email-message')
                .attr('data-from', (email.from || '').toLowerCase());
            var hdr = msg.append('div').attr('class', 'email-header');
            if(email.date)    hdr.append('div').html('<strong>Date:</strong> ' + email.date);
            if(email.from)    hdr.append('div').html('<strong>From:</strong> ' + email.from);
            if(email.to)      hdr.append('div').html('<strong>To:</strong> ' + email.to);
            if(email.subject) msg.append('div').attr('class', 'email-subject').text(email.subject);
            msg.append('pre').attr('class', 'email-body').text(email.body || '(no body)');
        });
    }

    var cached = emailContentCache[username];
    if(cached) {
        if(cached.data) render(cached.data[filepath]);
        return;
    }

    emailContentCache[username] = {data: null};
    panel.html('<em>Loading…</em>');

    var contentUrl = dataPath + 'email-content-' + username + '.json.gz';
    fetch(contentUrl)
        .then(function(r) {
            if(!r.ok) throw new Error(r.status);
            return r.arrayBuffer();
        })
        .then(function(buf) {
            return JSON.parse(pako.inflate(new Uint8Array(buf), {to: 'string'}));
        })
        .then(function(data) {
            emailContentCache[username] = {data: data};
            render(data[filepath]);
        })
        .catch(function() {
            emailContentCache[username] = {data: {}};
            panel.html('<em>Email content not available.</em>');
        });
}

d3.text(options.data + 'users.txt', function(error, users) {
    if(error) { console.error("couldn't read users.txt"); return; }
    var emails = {}, edges = [], addresses;
    var adjacent = {}, rawPersonThreads = {}, mostThreads;
    var followed = {}, person, proximity, selectedThreads = [];

    function getPersonThreads(p) {
        return (rawPersonThreads[p] || []).filter(function(t) {
            return new Set(t.hops.map(h => h.from)).size >= +options.nppl &&
                   t.hops.length >= +options.minhops;
        });
    }

    function read_threads(threads) {
        threads.forEach(function(t) {
            var froms = {};
            t.hops.reverse(); // should reverse in data source instead
            t.hops.forEach(function(h, i) {
                emails[h.from] = true;
                if(i > 0) {
                    var from = t.hops[i-1].from, to = t.hops[i].from;
                    console.assert(from && to);
                    edges.push({source: from, target: to});
                    adjacent[from] = adjacent[from] || {};
                    adjacent[from][to] = true;
                    adjacent[to] = adjacent[to] || {};
                    adjacent[to][from] = true;
                }
                if(!froms[h.from]) {
                    froms[h.from] = true;
                    rawPersonThreads[h.from] = rawPersonThreads[h.from] || [];
                    rawPersonThreads[h.from].push(t);
                }
            });
        });
    }

    function done() {
        mostThreads = Object.keys(rawPersonThreads)
            .filter(p => getPersonThreads(p).length > 0)
            .sort((a, b) => getPersonThreads(a).length - getPersonThreads(b).length);
        mostThreads = mostThreads
            .slice((mostThreads.length*100 - mostThreads.length*options.top)/100);
        addresses = mostThreads.sort();
        var nodes = ['--select an email address--'].concat(addresses);
        people.selectAll('option')
            .data(nodes, k => k)
          .enter().insert('option')
            .text(k => k)
            .attr('selected', k => k === options.user ? 'selected' : null);

        d3.range(2, 21).forEach(function(n) {
            d3.select('#nppl-select').append('option').attr('value', n).text(n)
                .property('selected', n === +options.nppl);
        });
        d3.range(1, 31).forEach(function(n) {
            d3.select('#minhops-select').append('option').attr('value', n).text(n)
                .property('selected', n === +options.minhops);
        });

        if(options.user)
            select_person(options.user);
    }

    function update_graph_data() {
        var nodes = proximity.nodes.slice(), edges = proximity.edges.slice();
        edges.forEach(function(e) {
            e.type = 'proximity';
            e.forward = e.backward = 0;
        });
        // deep copy followed
        var followed2 = Object.entries(followed).reduce(function(p, v) {
            p[v[0]] = Object.assign({}, v[1]);
            return p;
        }, {});
        // let there be node redundancy, since this crossfilter aggregation is identity
        selectedThreads.forEach(function(thread) {
            thread.hops.forEach(function(h, i) {
                nodes.push(h.from);
                if(i > 0) {
                    var s = thread.hops[i-1].from, t = thread.hops[i].from;
                    var e;
                    if(followed2[s] && (e = followed2[s][t])) {
                        e.type = 'thread';
                        ++e.forward;
                    } else if(followed2[t] && (e = followed2[t][s])) {
                        e.type = 'thread';
                        ++e.backward;
                    } else {
                        e = {source: s, target: t, type: 'thread', forward: 1, backward: 0};
                        followed2[s] = followed2[s] || {};
                        edges.push(followed2[s][t] = e);
                    }
                }
            });
        });
        var node_flat = dc_graph.flat_group.make(nodes, n => n),
            edge_flat = dc_graph.flat_group.make(edges, e => e.source + '->' + e.target);
        diagram
            .nodeDimension(node_flat.dimension).nodeGroup(node_flat.group)
            .edgeDimension(edge_flat.dimension).edgeGroup(edge_flat.group)
            .nodeStrokeWidth(n => n.key === person ? 3 : 1)
            .nodeStroke(n => n.key === person ? '#E34234' : 'black');
    }

    var people = d3.select('#people');
    var nread = 0;
    users = users.split(/\s/).slice(0, -1);
    console.assert(users.every(u => u));
    users.forEach(function(u) {
        d3.json(options.data + u, function(error, threads) {
            if(!error) read_threads(threads);
            ++nread;
            if(nread === users.length)
                done();
            d3.select('#progress')
                .html((nread < users.length ? 'read ' + u : 'Done') +
                      '<br>' + (nread === users.length ? 'Showing ' + mostThreads.length + '/' : '') + Object.keys(emails).length + ' addresses');
        });
    });

    function select_person(p, randomThread) {
        person = p;
        var allThreads = rawPersonThreads[person] || [];
        if(!allThreads.length) return;
        var prefixLength = allThreads[0].file.indexOf('/') + 1;
        function trim(tf) {
            return tf.slice(prefixLength);
        }
        var filteredThreads = getPersonThreads(person);
        var thread = d3.select('#threads').selectAll('div.thread-holder')
            .data(filteredThreads, t => t.file);
        thread
          .enter().append('div')
            .attr('class', 'thread-holder')
          .append('span')
            .attr('class', 'thread')
            .text(t => trim(t.file));
        thread.exit().remove();

        function select_thread(t, toggle) {
            var index = selectedThreads.indexOf(t);
            var wasIn = index !== -1;
            if(toggle) {
                if(wasIn)
                    selectedThreads.splice(index, 1);
                else
                    selectedThreads.push(t);
            } else {
                if(wasIn && selectedThreads.length === 1)
                    selectedThreads = [];
                else
                    selectedThreads = [t];
            }
            d3.select('#threads').selectAll('span.thread')
                .classed('selected', t2 => selectedThreads.indexOf(t2) !== -1);

            if(selectedThreads.length)
                show_email_content(selectedThreads[0], options.data);
            else
                d3.select('#email-panel').html('');

            starts = selectedThreads.map(t => t.hops[0].from);
            finishes = selectedThreads.map(t => t.hops[t.hops.length-1].from);
            update_graph_data();
            if(selectedThreads.length) {
                diagram
                    .edgeOpacity(thread_opacity(0.7))
                    .redraw();
                window.setTimeout(function() {
                    if(!wasIn) {
                        newThreads = [t];
                        spliner.avoidSharpTurns(false);
                        diagram
                            .edgeOpacity(thread_opacity(0.2));
                        reader.data(selectedThreads);
                        window.setTimeout(function() {
                            newThreads = [];
                            spliner.avoidSharpTurns(true);
                            reader.data(selectedThreads);
                        }, 5000);
                    } else reader.data(selectedThreads);
                }, 5000);
            } else reader.data(selectedThreads);
        }

        thread.select('span.thread').on('click', function(t) {
            select_thread.call(this, t, d3.event.shiftKey);
            options.thread = selectedThreads.length ? trim(selectedThreads[0].file) : '';
            replace_query_string();
        });

        proximity = radius(adjacent, followed = {}, person, +options.r, new Set(mostThreads));
        if(selectedThreads.length) {
            selectedThreads = [];
            starts = finishes = [];
            update_graph_data();
            diagram
                .edgeOpacity(thread_opacity(0.7))
                .render();
        } else {
            update_graph_data();
            diagram
                .edgeOpacity(thread_opacity(0.7))
                .render();
            if(randomThread)
                options.thread = trim(random_item(filteredThreads).file);
            if(options.thread) {
                // urls can get mangled by e.g. word processors
                if(options.thread.slice(-1) !== '.')
                    options.thread += '.';
                var selspan = d3.select('#threads').selectAll('span.thread').filter(t => trim(t.file) === options.thread);
                if(!selspan.size() && options.thread[options.thread-1] !== '.') {
                    options.thread += '.';
                    selspan = d3.select('#threads').selectAll('span.thread').filter(t => trim(t.file) === options.thread);
                }
                if(selspan.size())
                    select_thread.call(selspan.node(), selspan.datum());
                else {
                    console.warn('did not find thread', options.thread);
                    options.thread = '';
                }
                replace_query_string();
            }
        }
    }

    d3.select('#nppl-select').on('change', function() {
        options.nppl = this.value;
        if(person) select_person(person);
        replace_query_string();
    });
    d3.select('#minhops-select').on('change', function() {
        options.minhops = this.value;
        if(person) select_person(person);
        replace_query_string();
    });

    people.on('change', function() {
        select_person(this.value);
        options.user = this.value;
        replace_query_string();
    });
    d3.select('#random').on('click', function() {
        var randomUser = random_item(addresses);
        people.property('value', randomUser);
        options.user = randomUser;
        selectedThreads = [];
        select_person(randomUser, true);
    });
});
