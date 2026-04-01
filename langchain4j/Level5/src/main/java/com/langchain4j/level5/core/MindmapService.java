package com.langchain4j.level5.core;

import guru.nidi.graphviz.engine.Format;
import guru.nidi.graphviz.engine.Graphviz;
import guru.nidi.graphviz.model.Graph;
import guru.nidi.graphviz.model.Node;

import java.io.File;
import java.util.List;

import static guru.nidi.graphviz.model.Factory.graph;
import static guru.nidi.graphviz.model.Factory.node;

public class MindmapService {

    public String makeMindmap(List<String> lines) throws Exception {
        Graph g = graph("mindmap").directed();

        for (String line : lines) {
            String[] parts = line.split(":");
            if (parts.length != 2) continue;

            String root = parts[0].trim();
            String[] children = parts[1].split(",");

            Node rootNode = node(root);
            for (String child : children) {
                rootNode = rootNode.link(node(child.trim()));
            }

            g = g.with(rootNode);
        }

        File outDir = new File("mindmaps");
        if (!outDir.exists()) {
            outDir.mkdirs();
        }

        File out = new File(outDir, "mindmap_" + System.currentTimeMillis() + ".png");

        Graphviz.fromGraph(g).render(Format.PNG).toFile(out);

        return out.getAbsolutePath();
    }
}
