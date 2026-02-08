package com.langchain4j.level5.ingest;

import javax.swing.*;
import javax.swing.filechooser.FileNameExtensionFilter;
import java.io.File;
import java.util.ArrayList;
import java.util.List;

public class FileSelector {

    public static List<File> selectPdfFiles() {
        JFileChooser fileChooser = new JFileChooser();
        fileChooser.setMultiSelectionEnabled(true);
        fileChooser.setDialogTitle("Select documents to ingest");
        fileChooser.setFileSelectionMode(JFileChooser.FILES_ONLY);

        //  PDF, DOCX, TXT
        FileNameExtensionFilter filter = new FileNameExtensionFilter(
                "Supported Documents (*.pdf, *.docx, *.txt)", "pdf", "docx", "txt");
        fileChooser.setFileFilter(filter);

        List<File> selectedFiles = new ArrayList<>();
        int result = fileChooser.showOpenDialog(null);

        if (result == JFileChooser.APPROVE_OPTION) {
            File[] files = fileChooser.getSelectedFiles();
            for (File file : files) {
                String name = file.getName().toLowerCase();
                if (name.endsWith(".pdf") || name.endsWith(".docx") || name.endsWith(".txt")) {
                    selectedFiles.add(file);
                }
            }
        }

        return selectedFiles;
    }
}
